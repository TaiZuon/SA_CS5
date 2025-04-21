import aiohttp
import asyncio
import pymysql
import os
from dotenv import load_dotenv
import logging
from sidecar.log_writing import *
import time

# Khởi tạo logging
setup_logging()
# Load biến môi trường
load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
logging.basicConfig(
    level=log_resource_usage,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {TOKEN}"
}

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "tva",
    "database": "CS5"
}

def connect_db():
    log_resource_usage("Kết nối đến cơ sở dữ liệu...")
    return pymysql.connect(**DB_CONFIG)

def reset_db():
    log_resource_usage("Đang reset database...")
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        log_resource_usage("Đã tắt kiểm tra khóa ngoại.")
        cursor.execute("TRUNCATE TABLE `commit`;")
        log_resource_usage("Đã xóa dữ liệu trong bảng `commit`.")
        cursor.execute("TRUNCATE TABLE `release`;")
        log_resource_usage("Đã xóa dữ liệu trong bảng `release`.")
        cursor.execute("TRUNCATE TABLE `repo`;")
        log_resource_usage("Đã xóa dữ liệu trong bảng `repo`.")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        log_resource_usage("Đã bật lại kiểm tra khóa ngoại.")
        conn.commit()
        log_resource_usage("✅ Database đã được reset!")
    except Exception as e:
        logging.error(f"Lỗi khi reset database: {e}")
    finally:
        cursor.close()
        conn.close()

async def fetch_top_repos(session, per_page=10):
    start_time = time.time()  # Bắt đầu đo thời gian
    log_resource_usage("Đang fetch danh sách top repositories từ GitHub...")
    url = f"https://api.github.com/search/repositories?q=stars:>00&sort=stars&per_page={per_page}&page=1"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        repos = data.get("items", [])
        log_timing("Fetch top repositories", start_time, count=len(repos), unit="repositories")
        return repos

async def fetch_releases(session, owner, repo):
    start_time = time.time()  # Bắt đầu đo thời gian
    log_resource_usage(f"Đang fetch releases cho repository: {owner}/{repo}...")
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        releases = data if isinstance(data, list) else []
        log_timing(f"Fetch releases cho repository: {owner}/{repo}", start_time, count=len(releases), unit="releases")
        return releases

async def fetch_commits_by_release(session, owner, repo, tag_name):
    start_time = time.time()  # Bắt đầu đo thời gian
    log_resource_usage(f"Đang fetch commits cho release: {tag_name} trong repository: {owner}/{repo}...")
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={tag_name}&per_page=10"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        commits = data if isinstance(data, list) else []
        log_timing(f"Fetch commits for {owner}/{repo}@{tag_name}", start_time, count=len(commits), unit="commits")
        return commits
    
async def fetch_and_log_repos(session, per_page=10):
    """
    Fetch repositories, releases, và commits, đồng thời ghi log tổng hợp và thời gian cho từng repository.
    """
    start_time = time.time()  # Bắt đầu đo thời gian tổng
    repos = await fetch_top_repos(session, per_page=per_page)

    repo_releases = {}
    release_commits = {}
    total_releases = 0
    total_commits = 0

    # Thêm biến để tính tổng thời gian
    total_repo_time = 0
    total_release_time = 0
    total_commit_time = 0

    for repo in repos:
        repo_start_time = time.time()  # Bắt đầu đo thời gian cho repo này
        owner, repo_name = repo["owner"]["login"], repo["name"]
        logging.info(f"🔄 Bắt đầu xử lý repository: {owner}/{repo_name}")

        # Fetch releases
        release_start_time = time.time()
        releases = await fetch_releases(session, owner, repo_name)
        release_elapsed_time = time.time() - release_start_time
        total_release_time += release_elapsed_time

        if releases:
            repo_releases[repo["id"]] = releases
            total_releases += len(releases)

            # Fetch commits for each release
            for release in releases:
                commit_start_time = time.time()
                tag_name = release["tag_name"]
                commits = await fetch_commits_by_release(session, owner, repo_name, tag_name)
                commit_elapsed_time = time.time() - commit_start_time
                total_commit_time += commit_elapsed_time

                release_commits[release["id"]] = commits
                total_commits += len(commits)

        # Log thời gian xử lý cho repo này
        repo_elapsed_time = time.time() - repo_start_time
        total_repo_time += repo_elapsed_time
        logging.info(
            f"✅ Xử lý repository: {owner}/{repo_name} - Đã fetch được {len(releases)} releases và {len(release_commits.get(release['id'], [])) if releases else 0} commits trong {repo_elapsed_time:.2f} giây."
        )

    # Log tổng thời gian
    elapsed_time = time.time() - start_time
    logging.info(
        f"Fetch repo: Đã fetch được {len(repos)} repositories, {total_releases} releases, và {total_commits} commits trong {elapsed_time:.2f} giây."
    )

    # Tính thời gian trung bình
    avg_repo_time = total_repo_time / len(repos) if repos else 0
    avg_release_time = total_release_time / total_releases if total_releases else 0
    avg_commit_time = total_commit_time / total_commits if total_commits else 0

    

    return repos, repo_releases, release_commits, avg_repo_time, avg_release_time, avg_commit_time
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
                tag_name = release["tag_name"]
                content = release.get("body", "")[:65000]
                log_resource_usage(f"Lưu release: {tag_name} cho repository ID: {repo_id}...")
                cursor.execute(
                    "INSERT INTO `release` (id, content, repoID) VALUES (%s, %s, %s)",
                    (release_id, content, repo_id)
                )

        
    for repo_id, releases in repo_releases.items():
            for release in releases:
                release_id = release["id"]
                if release_id in release_commits:
                    for commit in release_commits[release_id]:
                        log_resource_usage(f"Lưu commit: {commit['sha']} cho release ID: {release_id}...")
                        cursor.execute(
                            "INSERT INTO `commit` (hash, message, releaseID) VALUES (%s, %s, %s)",
                            (commit["sha"], commit["commit"]["message"][:1000], release_id)
                        )

    conn.commit()
    log_resource_usage("✅ Dữ liệu đã lưu vào database!")

    # except Exception as e:
    #     logging.error(f"Lỗi khi lưu dữ liệu vào database: {e}")

    # finally:
    #     # Bật lại ràng buộc khóa ngoại
    #     cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    #     log_resource_usage("Đã bật lại kiểm tra khóa ngoại.")
    #     cursor.close()
    #     conn.close()

async def main():
    start_time = time.time()  # Bắt đầu đo thời gian tổng
    async with aiohttp.ClientSession() as session:
        # Chạy task theo dõi tài nguyên song song với chương trình chính
        tracking_task = asyncio.create_task(track_resource_usage())
        try:
            repos, repo_releases, release_commits, avg_repo_time, avg_release_time, avg_commit_time = await fetch_and_log_repos(session, per_page=50)
            reset_db()
            save_to_db(repos, repo_releases, release_commits)
        finally:
            tracking_task.cancel()  # Dừng task theo dõi khi chương trình chính hoàn thành
            try:
                await tracking_task
            except asyncio.CancelledError:
                pass

    elapsed_time = time.time() - start_time  # Tính thời gian tổng
    logging.info(f"Chương trình đã hoàn thành trong {elapsed_time:.2f} giây.")

    # Ghi log thời gian trung bình ở cuối file log
    logging.info(f"Thời gian trung bình fetch repository: {avg_repo_time:.2f} giây.")
    logging.info(f"Thời gian trung bình fetch release: {avg_release_time:.2f} giây.")
    logging.info(f"Thời gian trung bình fetch commit: {avg_commit_time:.2f} giây.")

    # Vẽ đồ thị
    from sidecar.log_writing import plot_metrics
    plot_metrics()

asyncio.run(main())
log_resource_usage("Tổng mức sử dụng tài nguyên")


