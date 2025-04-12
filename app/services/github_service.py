import aiohttp
from app.utils.github_repository import reset_db, save_to_db
from app.config.request import HEADERS
from bs4 import BeautifulSoup

# async def fetch_top_repos(session, per_page=5):
#   url = f"https://api.github.com/search/repositories?q=stars:>1000&sort=stars&per_page={per_page}"
#   async with session.get(url, headers=HEADERS) as resp:
#     return (await resp.json()).get("items", [])

# async def fetch_top_repos(session, per_page=100, total=1000):
#   repos = []
#   pages = total // per_page
#   for page in range(1, pages + 1):
#     url = f"https://api.github.com/search/repositories?q=stars:>1000&sort=stars&per_page={per_page}&page={page}"
#     async with session.get(url, headers=HEADERS) as resp:
#       data = await resp.json()
#       items = data.get("items", [])
#       repos.extend(items)
#   return repos

async def fetch_top_repos(session, total_pages=50):
  repos = []
  for page in range(1, total_pages + 1):
    url = f"https://gitstar-ranking.com/repositories?page={page}"
    async with session.get(url) as resp:
      html = await resp.text()
      soup = BeautifulSoup(html, "html.parser")
      for a in soup.select("a.list-group-item.paginated_item"):
        href = a["href"].strip("/")  # e.g. freeCodeCamp/freeCodeCamp
        user, name = href.split("/")
        repos.append({"user": user, "name": name})
  return repos

async def fetch_releases(session, owner, repo):
  releases = []
  page = 1
  while True:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100&page={page}"
    async with session.get(url, headers=HEADERS) as resp:
      data = await resp.json()
      if not isinstance(data, list) or len(data) == 0:
        break
    releases.extend(data)
    page += 1
  return releases

async def fetch_commits_by_release(session, owner, repo, tag, per_page=10):
  url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={tag}&per_page={per_page}"
  async with session.get(url, headers=HEADERS) as resp:
    return await resp.json()

# async def fetch_and_store_data(per_page):
#   async with aiohttp.ClientSession() as session:
#     repos = await fetch_top_repos(session, per_page)
#     repo_releases, release_commits = {}, {}
#     for repo in repos:
#       owner, repo_name = repo["owner"]["login"], repo["name"]
#       releases = await fetch_releases(session, owner, repo_name)
#       if isinstance(releases, list):
#         repo_releases[repo["id"]] = releases

#         for release in releases:
#           tag = release["tag_name"]
#           commits = await fetch_commits_by_release(session, owner, repo_name, tag)
#           release_commits[release["id"]] = commits

#     reset_db()
#     save_to_db(repos, repo_releases, release_commits)

async def fetch_and_store_data(total_pages=50):
  async with aiohttp.ClientSession() as session:
    repos = await fetch_top_repos(session, total_pages)
    repo_releases, release_commits = {}, {}
    for repo in repos:
      owner, repo_name = repo["user"], repo["name"]
      releases = await fetch_releases(session, owner, repo_name)
      if isinstance(releases, list):
        key = f"{owner}/{repo_name}"
        repo_releases[key] = releases

        for release in releases:
          tag = release.get("tag_name")
          if not tag:
            continue
          commits = await fetch_commits_by_release(session, owner, repo_name, tag)
          release_commits[release["id"]] = commits

  reset_db()
  save_to_db(repos, repo_releases, release_commits)