import aiohttp
from app.utils.github_repository import reset_db, save_to_db
from app.config.request import HEADERS

async def fetch_top_repos(session, per_page=5):
  url = f"https://api.github.com/search/repositories?q=stars:>1000&sort=stars&per_page={per_page}"
  async with session.get(url, headers=HEADERS) as resp:
    return (await resp.json()).get("items", [])

async def fetch_releases(session, owner, repo):
  url = f"https://api.github.com/repos/{owner}/{repo}/releases"
  async with session.get(url, headers=HEADERS) as resp:
    return await resp.json()

async def fetch_commits_by_release(session, owner, repo, tag, per_page=10):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={tag}&per_page={per_page}"
    async with session.get(url, headers=HEADERS) as resp:
      return await resp.json()

async def fetch_and_store_data(per_page):
    async with aiohttp.ClientSession() as session:
      repos = await fetch_top_repos(session, per_page)
      repo_releases, release_commits = {}, {}
      for repo in repos:
        owner, repo_name = repo["owner"]["login"], repo["name"]
        releases = await fetch_releases(session, owner, repo_name)
        if isinstance(releases, list):
          repo_releases[repo["id"]] = releases

          for release in releases:
            tag = release["tag_name"]
            commits = await fetch_commits_by_release(session, owner, repo_name, tag)
            release_commits[release["id"]] = commits

      reset_db()
      save_to_db(repos, repo_releases, release_commits)