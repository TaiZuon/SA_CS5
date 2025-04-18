import logging
import asyncio
from prometheus_client import Summary
from main_app.fetcher import (
    fetch_top_repos, fetch_releases,
    fetch_all_commits_by_tag, fetch_commits_between_tags
)
from main_app.database import save_repo, save_release, save_commit, save_commits_batch, delete_release
from sidecar.error_handler import safe_request

# Metric Prometheus để đo thời gian xử lý 1 repo
process_time = Summary('repo_process_seconds', 'Time spent processing a repo')

# Giới hạn đồng thời tối đa 5 task xử lý repo
sem = asyncio.Semaphore(5)

async def limited_process_repo(session, repo, idx):
    async with sem:
        await process_repo(session, repo, idx)

@process_time.time()
async def process_repo(session, repo, idx):
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    repo_id = repo["id"]

    logging.info(f"🚀 Processing repo #{idx}: {owner}/{repo_name}")
    try:
        # Lấy release
        releases = await safe_request(lambda token: fetch_releases(session, token, owner, repo_name), context=f"{owner}/{repo_name} - releases")
        if not releases:
            logging.info(f"⛔ Repo {owner}/{repo_name} không có release. Bỏ qua.")
            return

        releases.sort(key=lambda r: r.get("published_at") or "", reverse=False)
        prev_tag = None
        save_repo(repo)

        for release in releases:
            release_id = release["id"]
            tag_name = release.get("tag_name", "")

            save_release(release, repo_id)
            if not tag_name:
                continue

            try:
                if prev_tag:
                    commits = await safe_request(
                        lambda token: fetch_commits_between_tags(session, token, owner, repo_name, prev_tag, tag_name),
                        context=f"{owner}/{repo_name} - compare {prev_tag}...{tag_name}"
                    )
                else:
                    commits = await safe_request(
                        lambda token: fetch_all_commits_by_tag(session, token, owner, repo_name, tag_name),
                        context=f"{owner}/{repo_name}@{tag_name}"
                    )
                save_commits_batch(commits, release_id)

            except Exception as e:
                logging.warning(f"❌ Lỗi khi fetch commit cho {owner}/{repo_name}@{tag_name}: {e}. Rollback release.")
                delete_release(release_id)  # rollback
                break  # dừng hẳn nếu 1 release fail

            prev_tag = tag_name

    except Exception as e:
        logging.exception(f"🔥 Lỗi nghiêm trọng khi xử lý repo {repo['full_name']}: {e}")

async def collect_data(session):
    page_count = 50   # Tổng số trang cần thu thập dữ liệu

    for page in range(1, page_count + 1):
        try:
            # Lấy dữ liệu repos từ hàm fetch_top_repos
            repos_data = await fetch_top_repos(session, page=page)

            if not repos_data:
                logging.warning(f"❌ Không có dữ liệu từ page {page}")
                continue

            items = repos_data  # Dữ liệu repo từ trang hiện tại

        except Exception as e:
            logging.warning(f"❌ Bỏ qua page {page} vì lỗi: {e}")
            continue

        # Log số lượng repository đã thu thập được từ trang hiện tại
        logging.info(f"📦 Page {page}: {len(items)} repos")
        
        tasks = [limited_process_repo(session, repo, repo["id"]) for repo in items]
        await asyncio.gather(*tasks)
