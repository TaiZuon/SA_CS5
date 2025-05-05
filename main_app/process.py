import logging
import asyncio
import time
from packaging import version
from main_app.fetcher import (
    fetch_top_repos, fetch_releases,
    fetch_all_commits_by_tag, fetch_commits_between_tags
)
from main_app.database import connect_db, save_repo, save_release, save_commits_batch
from sidecar.log_writing import log_timing, log_resource_usage
from main_app.error_handler import safe_request
from main_app.sql_dumper import save_repo_sql, save_release_sql, save_commits_sql
from sidecar.metric_server import REQUEST_TIME, REPOS_PROCESSED, ACTIVE_TASKS, ERROR_COUNT
from asyncio import Queue
from main_app.config import SAVE_MODE

# Semaphore giới hạn xử lý đồng thời
sem = asyncio.Semaphore(100)
MAX_WORKERS = 100

async def limited_process_repo(session, repo, idx):
    async with sem:
        ACTIVE_TASKS.inc() 
        try:
            await process_repo(session, repo, idx)
        finally:
            ACTIVE_TASKS.dec()

async def repo_worker(session, queue: Queue, worker_id: int):
    while True:
        repo = await queue.get()
        if repo is None:
            logging.info(f"🛑 Worker {worker_id} dừng lại.")
            break
        await limited_process_repo(session, repo, repo["id"])
        queue.task_done()

@REQUEST_TIME.time()
async def process_repo(session, repo, idx):
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    repo_id = repo["id"]

    logging.info(f"🚀 Đang xử lý repo #{idx}: {owner}/{repo_name}")
    start_time = time.time()
    MAX_RETRIES = 3
    

    for attempt in range(1, MAX_RETRIES + 1):
        conn = connect_db()
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

            if SAVE_MODE == "sql":
                await save_repo_sql(repo)
            else:
                save_repo(repo)

            releases.sort(key=lambda r: r.get("published_at") or "", reverse=False)

            prev_tag = None
            for release in releases:
                await process_release(session, release, repo_id, owner, repo_name, prev_tag)
                prev_tag = release.get("tag_name", prev_tag)

            conn.commit()
            REPOS_PROCESSED.inc()
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
     
async def process_release(session, release, repo_id, owner, repo_name, prev_tag):
    tag_name = release.get("tag_name", "")
    release_id = release["id"]

    if SAVE_MODE == "sql":
        await save_release_sql(release, repo_id)
    else:
        save_release(release, repo_id)

    if not tag_name:
        logging.warning(f"⚠️ Release {release_id} không có tag_name. Bỏ qua.")
        return


    if prev_tag:
        # So sánh theo version để đảm bảo chiều đúng
        try:
            v_prev = version.parse(prev_tag)
            v_curr = version.parse(tag_name)
        except Exception:
            v_prev = prev_tag
            v_curr = tag_name
        base, head = (prev_tag, tag_name) if v_prev <= v_curr else (tag_name, prev_tag)

        commits = await safe_request(
            lambda token: fetch_commits_between_tags(session, token, owner, repo_name, base, head),
            context=f"{owner}/{repo_name} - compare {base}...{head}"
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

async def collect_data(session, repo_limit=5000):
    """Thu thập dữ liệu repo với số lượng giới hạn, xử lý song song bằng các worker."""
    repo_queue = Queue()

    # Tạo worker để xử lý repo song song
    workers = [asyncio.create_task(repo_worker(session, repo_queue, i)) for i in range(MAX_WORKERS)]

    try:
        repos_data = await fetch_top_repos(session, limit=repo_limit)
        if not repos_data:
            logging.warning("❌ Không fetch được repo nào.")
            return

        logging.info(f"📦 Tổng cộng: {len(repos_data)} repo sẽ được xử lý.")

        for repo in repos_data:
            await repo_queue.put(repo)

    except Exception as e:
        logging.error(f"❌ Lỗi khi fetch top repos: {e}")
        return

    # Đợi hàng đợi xử lý xong
    await repo_queue.join()

    # Gửi tín hiệu dừng đến các worker
    for _ in range(MAX_WORKERS):
        await repo_queue.put(None)

    await asyncio.gather(*workers)
