import logging
from main_app.config import GITHUB_API_URL, GITSTAR_RANKING_URL
from bs4 import BeautifulSoup
from main_app.error_handler import handle_github_error
# Biến đếm số lần fetch
fetch_counters = {
    "repos": 0,
    "releases": 0,
    "compare": 0,
    "commits": 0
}

# Tạo headers dùng chung
def build_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "RepoFetcher 0.0.1"
    }

async def fetch_top_repos(session, limit=5000):
    """Fetch top repositories từ Gitstar Ranking, với số lượng giới hạn tùy chọn"""
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
                break  # Không còn dữ liệu

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
    fetch_counters["releases"] += 1

    headers = build_headers(token)
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases"
    logging.info(f"📦 Fetching releases for {owner}/{repo} (Releases Fetch #{fetch_counters['releases']})")

    async with session.get(url, headers=headers) as resp:
        try:
            data = await resp.json()

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                logging.warning(f"⚠️ Dữ liệu releases không phải list hoặc dict: {data}")
                return []
        except Exception as e:
            logging.error(f"❌ Lỗi khi parse JSON từ API releases: {e}")
            return []

async def fetch_commits_between_tags(session, token, owner, repo, base_tag, head_tag):
    fetch_counters["compare"] += 1

    headers = build_headers(token)
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/compare/{base_tag}...{head_tag}"
    logging.info(f"🔀 Comparing tags {base_tag}...{head_tag} for {owner}/{repo} (Compare Fetch #{fetch_counters['compare']})")

    async with session.get(url, headers=headers) as resp:
        data = await resp.json()
        return data.get("commits", [])

async def fetch_all_commits_by_tag(session, token, owner, repo, tag_name):
    headers = build_headers(token)
    all_commits = []
    page = 1
    per_page = 100

    while True:
        fetch_counters["commits"] += 1

        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?sha={tag_name}&per_page={per_page}&page={page}"
        logging.info(f"📜 Fetching commits page {page} for {owner}/{repo}@{tag_name} (Commits Fetch #{fetch_counters['commits']})")

        async with session.get(url, headers=headers) as resp:
            commits = await resp.json()
            if not commits or not isinstance(commits, list):
                break

            all_commits.extend(commits)
            page += 1

    logging.info(f"✅ Total {len(all_commits)} commits fetched for {owner}/{repo}@{tag_name}")
    return all_commits
