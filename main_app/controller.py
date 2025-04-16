import logging
from main_app.fetcher import fetch_top_repos, fetch_releases, fetch_commits_by_tag, fetch_all_commits_by_tag, fetch_commits_between_tags
from main_app.database import save_repo, save_release, save_commit, save_commits_batch
from sidecar.token_rotator import get_valid_token
from prometheus_client import Summary
import asyncio

# Tạo metric để đo thời gian xử lý từng repo
process_time = Summary('repo_process_seconds', 'Time spent processing a repo')

# Giới hạn tối đa 5 task chạy đồng thời
sem = asyncio.Semaphore(5)

async def limited_process_repo(session, repo, idx):
    async with sem:
        await process_repo(session, repo, idx)

@process_time.time()
async def process_repo(session, repo, idx):
    try:
        
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        repo_id = repo["id"]

        logging.info(f"Processing repo number {idx}: {repo_name}")

        token = get_valid_token()
        releases = await fetch_releases(session, token, owner, repo_name)

        if not releases:  # Bỏ qua repo không có release
            logging.info(f"🚫 Repo {owner}/{repo_name} không có release. Bỏ qua.")
            return
        
        # Sắp xếp releases theo published_at (từ cũ đến mới)
        releases.sort(key=lambda r: r.get("published_at") or "", reverse=False)

        prev_tag = None

        # Lưu repo ngay
        save_repo(repo)

        for release in releases:
            release_id = release["id"]
            tag_name = release.get("tag_name", "")

            # Lưu release ngay
            save_release(release, repo_id)

            if not tag_name:
                continue

            token = get_valid_token()
            if prev_tag:
                token = get_valid_token()
                commits = await fetch_commits_between_tags(session, token, owner, repo_name, prev_tag, tag_name)
            else:
                token = get_valid_token()
                commits = await fetch_commits_by_tag(session, token, owner, repo_name, tag_name)

            # for commit in commits:
            #     save_commit(commit, release_id)
            save_commits_batch(commits, release_id)

            prev_tag = tag_name

    except Exception as e:
        logging.warning(f"Lỗi xử lý repo {repo['full_name']}: {e}")

async def collect_data(session):
    page_count = 10
    per_page = 100

    for page in range(1, page_count + 1):
        token = get_valid_token()
        repos_data = await fetch_top_repos(session, token, page=page, per_page=per_page)
        items = repos_data.get("items", [])

        logging.info(f"📦 Page {page}: {len(items)} repos")

        tasks = []
        for idx, repo in enumerate(items, start=1 + (page - 1) * per_page):
            # logging.info(f"🔍 Repo number: {idx} - {repo['full_name']}")
            tasks.append(limited_process_repo(session, repo, idx))

        # Đợi tất cả các repo trong trang này xử lý xong (tối đa 5 chạy song song)
        await asyncio.gather(*tasks)
