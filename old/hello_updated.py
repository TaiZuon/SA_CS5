import requests
import pymysql
import os
import aiohttp
from dotenv import load_dotenv
import logging
from sidecar.log_writing import setup_logging, log_resource_usage, log_timing
import time
from sidecar.metric_server import start_metrics_server, REPOS_PROCESSED
import asyncio
# Khởi tạo logging
setup_logging()
# Load biến môi trường
load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {TOKEN}",
    "User-Agent": "RepoFetcher 0.0.1"
}

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAMEs", "github_data"),
    "port": int(os.getenv("DB_PORT", 3307))
}

def connect_db():
    return pymysql.connect(**DB_CONFIG)

def reset_db():
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        cursor.execute("TRUNCATE TABLE `commit`;")
        cursor.execute("TRUNCATE TABLE `release`;")
        cursor.execute("TRUNCATE TABLE `repo`;")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        conn.commit()
    except Exception as e:
        logging.error(f"Lỗi khi reset database: {e}")
    finally:
        cursor.close()
        conn.close()

async def fetch_top_repos(per_page=100, total=200):
    start_time = time.time()
    repos = []
    pages = (total + per_page - 1) // per_page  # Tính số trang cần fetch

    async with aiohttp.ClientSession() as session:
        for page in range(1, pages + 1):
            url = f"https://api.github.com/search/repositories?q=stars:>0&sort=stars&per_page={per_page}&page={page}"
            async with session.get(url, headers=HEADERS) as response:
                data = await response.json()
                items = data.get("items", [])
                repos.extend(items)
                logging.info(f"✅ Fetched {len(items)} repos từ trang {page}")

    log_timing("Fetch top repositories", start_time, count=len(repos), unit="repositories")
    return repos[:total]  # Đảm bảo chỉ lấy đúng số lượng yêu cầu

async def fetch_releases(owner, repo):
    start_time = time.time()
    log_resource_usage(f"Đang fetch releases cho repository: {owner}/{repo}...")
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                text = await response.text()
                logging.warning(f"⚠️ Lỗi khi fetch releases cho {owner}/{repo}: {response.status} - {text}")
                return []
            data = await response.json()
            releases = data if isinstance(data, list) else []

    log_timing(f"Fetch releases cho repository: {owner}/{repo}", start_time, count=len(releases), unit="releases")
    return releases

async def fetch_commits_between_tags(owner, repo, base_tag, head_tag):
    url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base_tag}...{head_tag}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            data = await response.json()
            commits = data.get("commits", [])
    
    return commits

async def fetch_all_commits_by_tag(owner, repo, tag_name):
    all_commits = []
    page = 1
    per_page = 100

    async with aiohttp.ClientSession() as session:
        while True:
            url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={tag_name}&per_page={per_page}&page={page}"
            async with session.get(url, headers=HEADERS) as response:
                commits = await response.json()
                
                if not commits or not isinstance(commits, list):
                    break
                
                all_commits.extend(commits)
                page += 1

    return all_commits

async def fetch_and_log_repos(per_page=100, total=200):
    start_time = time.time()
    repos = await fetch_top_repos(per_page=per_page, total=total)

    repo_releases = {}
    release_commits = {}
    total_releases = 0
    total_commits = 0

    total_repo_time = 0
    total_release_time = 0
    total_commit_time = 0

    # Loại bỏ list tasks, thay vào đó chạy tuần tự mỗi repo
    for repo in repos:
        await process_repo(repo, repo_releases, release_commits, total_releases, total_commits,
                           total_repo_time, total_release_time, total_commit_time)

    elapsed_time = time.time() - start_time
    logging.info(
        f"🏁 Tổng kết: {len(repos)} repositories, {total_releases} releases, {total_commits} commits "
        f"trong {elapsed_time:.2f} giây."
    )

    avg_repo_time = total_repo_time / len(repos) if repos else 0
    avg_release_time = total_release_time / total_releases if total_releases else 0
    avg_commit_time = total_commit_time / total_commits if total_commits else 0

    return repos, repo_releases, release_commits, avg_repo_time, avg_release_time, avg_commit_time

async def process_repo(repo, repo_releases, release_commits, total_releases, total_commits,
                       total_repo_time, total_release_time, total_commit_time):
    repo_start_time = time.time()
    owner, repo_name = repo["owner"]["login"], repo["name"]
    logging.info(f"🔄 Bắt đầu xử lý repository: {owner}/{repo_name}")

    release_start_time = time.time()
    releases = await fetch_releases(owner, repo_name)
    release_elapsed_time = time.time() - release_start_time
    total_release_time += release_elapsed_time

    if releases:
        repo_releases[repo["id"]] = releases
        total_releases += len(releases)

        for idx, release in enumerate(releases):
            tag_name = release.get("tag_name")
            release_id = release.get("id")

            if not tag_name:
                logging.warning(f"⚠️ Release {release_id} không có tag_name. Bỏ qua.")
                continue

            logging.info(f"📦 Release {idx + 1}/{len(releases)}: tag = `{tag_name}` (ID: {release_id})")

            commit_start_time = time.time()

            prev_tag = releases[idx - 1]["tag_name"] if idx > 0 else None

            if prev_tag:
                logging.info(f"🔍 So sánh commit từ `{prev_tag}` đến `{tag_name}`...")
                commits = await fetch_commits_between_tags(owner, repo_name, prev_tag, tag_name)
            else:
                logging.info(f"🔍 Fetch toàn bộ commit từ tag `{tag_name}` (release đầu tiên)...")
                commits = await fetch_all_commits_by_tag(owner, repo_name, tag_name)

            commit_elapsed_time = time.time() - commit_start_time
            total_commit_time += commit_elapsed_time

            release_commits[release_id] = commits
            total_commits += len(commits)

    repo_elapsed_time = time.time() - repo_start_time
    total_repo_time += repo_elapsed_time
    logging.info(
        f"✅ Xong repository: {owner}/{repo_name} - {len(releases)} releases, "
        f"{sum(len(release_commits.get(release['id'], [])) for release in releases)} commits "
        f"trong {repo_elapsed_time:.2f} giây."
    )

def save_to_db(repos, repo_releases, release_commits):
    log_resource_usage("Đang lưu dữ liệu vào database...")
    conn = connect_db()
    cursor = conn.cursor()

    # Lưu dữ liệu vào bảng `release` trước
    for repo in repos:
        log_resource_usage(f"Lưu repository: {repo['name']}...")
        cursor.execute(
            "INSERT INTO `repo` (id, user, name) VALUES (%s, %s, %s)",
            (repo["id"], repo["owner"]["login"], repo["name"])
        )

    for repo_id, releases in repo_releases.items():
        for release in releases:
            release_id = release["id"]
            tag_name = release.get("tag_name", "")
            content = release.get("body", "")[:65000]
            log_resource_usage(f"Lưu release: {tag_name} cho repository ID: {repo_id}...")
            cursor.execute(
                "INSERT INTO `release` (id, content, repoID) VALUES (%s, %s, %s)",
                (release_id, content, repo_id)
            )

            # Lưu commits tương ứng nếu có
            if release_id in release_commits:
                for commit in release_commits[release_id]:
                    log_resource_usage(f"Lưu commit: {commit['sha']} cho release ID: {release_id}...")
                    cursor.execute(
                        "INSERT INTO `commit` (hash, message, releaseID) VALUES (%s, %s, %s)",
                        (commit["sha"], commit["commit"]["message"][:1000], release_id)
                    )

    conn.commit()
    cursor.close()
    conn.close()
    log_resource_usage("✅ Dữ liệu đã lưu vào database!")

async def main():
    start_time = time.time()
    metrics_task = start_metrics_server(port=8000, update_interval=5)

    reset_db()
    repos, repo_releases, release_commits, avg_repo_time, avg_release_time, avg_commit_time = await fetch_and_log_repos(per_page=15, total=15)

    # Chạy save_to_db trong thread để không block event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, save_to_db, repos, repo_releases, release_commits)

    elapsed_time = time.time() - start_time
    logging.info(f"Chương trình đã hoàn thành trong {elapsed_time:.2f} giây.")


if __name__ == "__main__":
    asyncio.run(main())
