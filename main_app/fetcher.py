import logging
from bs4 import BeautifulSoup
from main_app.config import GITHUB_API_URL, GITSTAR_RANKING_URL
from main_app.error_handler import handle_github_error

fetch_counters = {
    "repos": 0,
    "releases": 0,
    "compare": 0,
    "commits": 0
}

def build_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "RepoFetcher 0.0.1"
    }

async def fetch_top_repos(session, limit=5000):
    items = []
    page = 1

    while len(items) < limit:
        fetch_counters["repos"] += 1
        url = f"{GITSTAR_RANKING_URL}/repositories?page={page}"
        logging.info(f"🔎 Fetching repos page {page} (Repos Fetch #{fetch_counters['repos']})")

        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            repo_links = soup.select("a.list-group-item.paginated_item")

            if not repo_links:
                logging.warning("⚠️ Không còn repo nào để fetch.")
                break

            for idx, a in enumerate(repo_links, start=1):
                if len(items) >= limit:
                    break

                href = a["href"].strip("/")
                user, name = href.split("/")
                repo_id = (page - 1) * 100 + idx

                repo = {
                    "owner": {"login": user},
                    "name": name,
                    "id": repo_id
                }
                items.append(repo)

        page += 1

    logging.info(f"✅ Đã fetch {len(items)} repo.")
    return items

async def fetch_releases(session, token, owner, repo):
    headers = build_headers(token)
    releases = []
    page = 1
    per_page = 100

    while True:
        fetch_counters["releases"] += 1
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases?page={page}&per_page={per_page}"
        logging.info(f"📦 [releases] {owner}/{repo} - page {page} (#{fetch_counters['releases']})")

        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                reset_ts = None
                reset_info = None
                if resp.status == 403:
                    # Lỗi 403 Forbidden, có thể do rate limit
                    reset_ts = resp.headers.get("X-RateLimit-Reset")
                reset_info = f"reset_ts={reset_ts}" if reset_ts else "reset_ts=unknown"
                raise Exception(f"[releases] {owner}/{repo} - HTTP {resp.status} - {reset_info}")
            data = await resp.json()

            if not isinstance(data, list):
                logging.warning(f"⚠️ [releases] {owner}/{repo} - Response không phải list, ép thành list.")
                data = [data]

            if not data:
                break

            releases.extend(data)
            page += 1

    logging.info(f"✅ [releases] {owner}/{repo} - Tổng {len(releases)} release(s) fetched.")
    return releases

async def fetch_commits_between_tags(session, token, owner, repo, base_tag, head_tag):
    fetch_counters["compare"] += 1
    headers = build_headers(token)
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/compare/{base_tag}...{head_tag}"
    logging.info(f"🔀 [compare] {owner}/{repo} {base_tag}...{head_tag} (#{fetch_counters['compare']})")

    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
                reset_ts = None
                reset_info = None
                if resp.status == 403:
                    # Lỗi 403 Forbidden, có thể do rate limit
                    reset_ts = resp.headers.get("X-RateLimit-Reset")
                reset_info = f"reset_ts={reset_ts}" if reset_ts else "reset_ts=unknown"
                raise Exception(f"[releases] {owner}/{repo} - HTTP {resp.status} - {reset_info}")
        data = await resp.json()
        commits = data.get("commits", [])
        logging.info(f"✅ [compare] {owner}/{repo} - {len(commits)} commits between {base_tag}...{head_tag}")
        return commits

async def fetch_all_commits_by_tag(session, token, owner, repo, tag_name):
    headers = build_headers(token)
    all_commits = []
    page = 1
    per_page = 100

    while True:
        fetch_counters["commits"] += 1
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?sha={tag_name}&per_page={per_page}&page={page}"
        logging.info(f"📜 [commits] {owner}/{repo}@{tag_name} - page {page} (#{fetch_counters['commits']})")

        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                reset_ts = None
                reset_info = None
                if resp.status == 403:
                    # Lỗi 403 Forbidden, có thể do rate limit
                    reset_ts = resp.headers.get("X-RateLimit-Reset")
                reset_info = f"reset_ts={reset_ts}" if reset_ts else "reset_ts=unknown"
                raise Exception(f"[releases] {owner}/{repo} - HTTP {resp.status} - {reset_info}")
            commits = await resp.json()

            if not isinstance(commits, list):
                logging.warning(f"⚠️ [commits] {owner}/{repo}@{tag_name} - Response không phải list.")
                commits = [commits]

            if not commits:
                break

            all_commits.extend(commits)
            page += 1

    logging.info(f"✅ [commits] {owner}/{repo}@{tag_name} - Tổng {len(all_commits)} commits.")
    return all_commits
