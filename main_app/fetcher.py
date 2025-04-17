import aiohttp
import logging
from main_app.config import GITHUB_API_URL
from sidecar.error_handler import handle_github_error_with_retry

# Tạo headers dùng chung
def build_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "de bo phet cho 0.0.1"
    }

async def fetch_top_repos(session, token, per_page=50, page=1):
    headers = build_headers(token)
    url = f"{GITHUB_API_URL}/search/repositories?q=stars:>0&sort=stars&per_page={per_page}&page={page}"
    logging.info(f"🔎 Fetching repos page {page}")
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            should_abort = await handle_github_error_with_retry(resp, token, context=f"repos page {page}")
            if should_abort:
                return None
        return await resp.json()

async def fetch_releases(session, token, owner, repo):
    headers = build_headers(token)
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases"
    logging.info(f"📦 Fetching releases for {owner}/{repo}")
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            should_abort = await handle_github_error_with_retry(resp, token, context=f"{owner}/{repo} - releases")
            if should_abort:
                return None
        return await resp.json()

async def fetch_commits_between_tags(session, token, owner, repo, base_tag, head_tag):
    headers = build_headers(token)
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/compare/{base_tag}...{head_tag}"
    async with session.get(url, headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("commits", [])
        else:
            should_abort = await handle_github_error_with_retry(resp, token, context=f"{owner}/{repo} - compare {base_tag}...{head_tag}")
            if should_abort:
                return None
            return []

async def fetch_commits_by_tag(session, token, owner, repo, tag_name):
    headers = build_headers(token)
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?sha={tag_name}&per_page=10"
    logging.info(f"📜 Fetching commits for {owner}/{repo} (tag: {tag_name})")
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            should_abort = await handle_github_error_with_retry(resp, token, context=f"{owner}/{repo}@{tag_name}")
            if should_abort:
                return None
        return await resp.json()

async def fetch_all_commits_by_tag(session, token, owner, repo, tag_name):
    headers = build_headers(token)
    all_commits = []
    page = 1
    per_page = 100

    while True:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?sha={tag_name}&per_page={per_page}&page={page}"
        logging.info(f"📜 Fetching commits page {page} for {owner}/{repo}@{tag_name}")
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                should_abort = await handle_github_error_with_retry(resp, token, context=f"{owner}/{repo}@{tag_name} - page {page}")
                if should_abort:
                    break

            commits = await resp.json()
            if not commits or not isinstance(commits, list):
                break

            all_commits.extend(commits)
            page += 1

    logging.info(f"✅ Total {len(all_commits)} commits fetched for {owner}/{repo}@{tag_name}")
    return all_commits
