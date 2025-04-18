import logging
import asyncio
import time
from prometheus_client import Summary
from main_app.fetcher import (
    fetch_top_repos, fetch_releases, fetch_commits_by_tag,
    fetch_all_commits_by_tag, fetch_commits_between_tags
)
from sidecar.log_writing import log_timing, log_resource_usage
from sidecar.error_handler import safe_request
from main_app.database import connect_db

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

            releases.sort(key=lambda r: r.get("published_at") or "", reverse=False)
            prev_tag = None

            # Save repo
            cursor.execute(
                "INSERT INTO `repo` (id, user, name) VALUES (%s, %s, %s)",
                (repo["id"], repo["owner"]["login"], repo["name"])
            )

            for release in releases:
                release_id = release["id"]
                tag_name = release.get("tag_name", "")

                # Save release
                cursor.execute(
                    "INSERT INTO `release` (id, content, repoID) VALUES (%s, %s, %s)",
                    (release_id, release.get("body", "")[:65000], repo_id)
                )

                if not tag_name:
                    continue

                # Fetch commits
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

                # Save commits
                commit_data = [
                    (commit["sha"], commit["commit"]["message"][:1000], release_id)
                    for commit in commits
                ]
                cursor.executemany(
                    "INSERT INTO `commit` (hash, message, releaseID) VALUES (%s, %s, %s)",
                    commit_data
                )

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
    page_count = 50
    per_page = 100

    for page in range(1, page_count + 1):
        try:
            repos_data = await safe_request(
                lambda token: fetch_top_repos(session, token, page=page, per_page=per_page),
                context=f"repos page {page}"
            )
            items = repos_data.get("items", [])
        except Exception as e:
            logging.warning(f"❌ Bỏ qua page {page} vì lỗi: {e}")
            continue

        logging.info(f"📦 Page {page}: {len(items)} repos")
        tasks = [
            limited_process_repo(session, repo, idx)
            for idx, repo in enumerate(items, start=1 + (page - 1) * per_page)
        ]
        await asyncio.gather(*tasks)
