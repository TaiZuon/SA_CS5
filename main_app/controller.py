import logging
import asyncio
import time
from prometheus_client import Summary
from main_app.fetcher import (
    fetch_top_repos, fetch_releases,
    fetch_all_commits_by_tag, fetch_commits_between_tags
)
from main_app.database import connect_db, save_repo, save_release, save_commits_batch
from sidecar.log_writing import log_timing, log_resource_usage
from sidecar.error_handler import safe_request
from sidecar.sql_dumper import save_repo_sql, save_release_sql, save_commits_sql
from sidecar.schema_dumper import write_schema_if_needed
from asyncio import Queue
from main_app.config import SAVE_MODE

# Prometheus metric
process_time = Summary('repo_process_seconds', 'Time spent processing a repo')

# Semaphore giới hạn xử lý đồng thời
sem = asyncio.Semaphore(10)
MAX_WORKERS = 15

async def limited_process_repo(session, repo, idx):
    async with sem:
        await process_repo(session, repo, idx)

async def repo_worker(session, queue: Queue, worker_id: int):
    while True:
        repo = await queue.get()
        if repo is None:
            logging.info(f"🛑 Worker {worker_id} dừng lại.")
            break
        await limited_process_repo(session, repo, repo["id"])
        queue.task_done()

@process_time.time()
async def process_repo(session, repo, idx):
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    repo_id = repo["id"]

    logging.info(f"🚀 Đang xử lý repo #{idx}: {owner}/{repo_name}")
    start_time = time.time()
    MAX_RETRIES = 3

    for attempt in range(1, MAX_RETRIES + 1):
        conn = connect_db()
        # logging.info(f"🔄 Kết nối đến database để xử lý repo {owner}/{repo_name} (attempt {attempt})")
        cursor = conn.cursor()
        
        try:
            conn.begin()

            releases = await safe_request(
                lambda token: fetch_releases(session, token, owner, repo_name),
                context=f"{owner}/{repo_name} - releases"
            )

            if not releases:
                logging.info(f"⛔ Repo {owner}/{repo_name} không có release. Bỏ qua.")
                return

            # Sort tăng dần theo publish date
            releases.sort(key=lambda r: r.get("published_at") or "", reverse=False)

            # Lưu repo
            if SAVE_MODE == "sql":
                await save_repo_sql(repo)
            else:
                save_repo(repo)

            prev_tag = None
            for release in releases:
                release_id = release["id"]
                tag_name = release.get("tag_name", "")

                if SAVE_MODE == "sql":
                    await save_release_sql(release, repo_id)
                else:
                    save_release(release, repo_id)

                if not tag_name:
                    continue

                # Fetch commit
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

                if SAVE_MODE == "sql":
                    await save_commits_sql(commits, release_id)
                else:
                    save_commits_batch(commits, release_id)
                prev_tag = tag_name

            conn.commit()
            logging.info(f"✅ Repo {owner}/{repo_name} xử lý thành công (attempt {attempt})")
            log_timing("Process Repo", start_time, unit="releases", count=len(releases))
            log_resource_usage(f"Repo {owner}/{repo_name}")
            return

        except Exception as e:
            conn.rollback()
            logging.warning(f"⚠️ Attempt {attempt}/{MAX_RETRIES} failed for {owner}/{repo_name}: {e}")
            if attempt < MAX_RETRIES:
                logging.info("🔁 Thử lại sau 2s...")
                await asyncio.sleep(2)
            else:
                logging.error(f"⛔ Bỏ qua repo {owner}/{repo_name} sau {MAX_RETRIES} lần thử.")
        finally:
            cursor.close()
            conn.close()

async def collect_data(session):
    page_count = 1
    repo_queue = Queue()
    workers = [asyncio.create_task(repo_worker(session, repo_queue, i)) for i in range(MAX_WORKERS)]

    for page in range(1, page_count + 1):
        # start_time = time.time()
        try:
            repos_data = await fetch_top_repos(session, page=page)
            if not repos_data:
                logging.warning(f"❌ Không có dữ liệu từ page {page}")
                continue
            items = repos_data
        except Exception as e:
            logging.warning(f"❌ Bỏ qua page {page} vì lỗi: {e}")
            continue

        logging.info(f"📦 Page {page}: {len(items)} repos")

        for repo in items:
            await repo_queue.put(repo)
            # logging.info(f"🔄 Đã thêm repo {repo['owner']['login']}/{repo['name']} vào hàng đợi")

    await repo_queue.join()

    # Gửi tín hiệu dừng đến các worker
    for _ in range(MAX_WORKERS):
        await repo_queue.put(None)
    await asyncio.gather(*workers)
