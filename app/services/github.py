import aiohttp
from app.utils.write_database.insert_methods import simple_insert_to_db, batch_save_to_db
from app.utils.write_database.reset_db import reset_db
from app.config.request import HEADERS
from bs4 import BeautifulSoup
import time
import asyncio
import random
from aiohttp_socks import ProxyConnector


MAX_CONCURRENT_REQUESTS = 5

# Semaphore để giới hạn số lượng requests đồng thời
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


# Function to fetch top repositories from GitStar ranking
# Each page contains a list of 100 repositories, and by fetching 50 pages, 
# we can retrieve up to 5000 repositories in total.
async def fetch_top_repos(session, total_pages=50):
  repos = []
  for page in range(1, total_pages + 1):
    # Construct the URL to get the repository list for the current page
    url = f"https://gitstar-ranking.com/repositories?page={page}"

    async with session.get(url) as resp:

      # Fetch the HTML content of the page
      html = await resp.text()

      # Parse the HTML content using BeautifulSoup
      soup = BeautifulSoup(html, "html.parser")

      # Loop through all repository items on the page
      for a in soup.select("a.list-group-item.paginated_item"):
        # Extract the user/repository path, e.g., 'freeCodeCamp/freeCodeCamp'
        href = a["href"].strip("/")

        # Split the path into user and repository name
        user, name = href.split("/")

        # Add the repository info to the list
        repos.append({"user": user, "name": name})
  return repos

# Function to fetch releases of a repository from GitHub API
# Each page contains up to 100 releases. This function continues fetching releases 
# until all releases are retrieved for the given repository.
async def fetch_releases(session, owner, repo):
    releases = []
    page = 1
    while True:
        # Construct the URL to fetch releases for the given repository and page
        url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100&page={page}"

        async with session.get(url, headers=HEADERS) as resp:
            # Parse the JSON response
            data = await resp.json()

            await asyncio.sleep(random.uniform(3.0, 5.0))

            # Check rate limit or unexpected response
            if not isinstance(data, list):
                # Check if rate limit is reached by inspecting response headers
                remaining = resp.headers.get("X-RateLimit-Remaining")

                if remaining == '0':
                    reset_time = int(resp.headers.get("X-RateLimit-Reset", time.time()))  # When the limit resets
                    wait_time = reset_time - int(time.time()) + 5  # Wait 5 seconds after reset time
                    print(f"[⛔] Rate limit reached, waiting for {wait_time} seconds...")
                    await asyncio.sleep(wait_time)  # Sleep before retrying
                    continue
                else:
                    print("[⛔] Unexpected response when fetching releases.")
                    print(data)
                    break

            # Break if there are no more releases
            if len(data) == 0:
                break

        # Add the releases to the list
        releases.extend(data)

        # Move to the next page of releases
        page += 1
    return releases

# Function to fetch all commits associated with a specific release (by tag) from GitHub API
# This function paginates through all available commits for the given tag
async def fetch_commits_by_release(session, owner, repo, tag):
  commits = []
  page = 1

  while True:
    # Construct the paginated URL to fetch commits by tag
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={tag}&per_page=100&page={page}"
    
    async with session.get(url, headers=HEADERS) as resp:
      data = await resp.json()

      await asyncio.sleep(random.uniform(3.0, 5.0))

      # Break if no more commits are returned
      if not isinstance(data, list) or len(data) == 0:
        break

    # Append the fetched commits to the list
    commits.extend(data)

    # Move to the next page
    page += 1

  return commits

# Main function to fetch top repositories, their releases, and corresponding commits,
# then reset the database and store all fetched data
async def fetch_and_store_data(total_pages=50):
  connector = ProxyConnector.from_url('socks5://127.0.0.1:9050')  # Proxy via Tor's default port
  async with aiohttp.ClientSession(connector=connector) as session:
        
    repos = await fetch_top_repos(session, total_pages)
    
    reset_db()
    start_time = time.time()

    async def process_repo(repo):
      owner, repo_name = repo["user"], repo["name"]
      full_name = f"{owner}/{repo_name}"

      # Use semaphore to limit the number of concurrent requests
      async with semaphore:
        await asyncio.sleep(random.uniform(3.0, 5.0))

        releases = await fetch_releases(session, owner, repo_name)
        print(f"🔁 Found {len(releases)} releases for {full_name}")

        repo_releases = {}
        release_commits = {}

        if releases and len(releases) > 0:
          repo_releases[f"{owner}/{repo_name}"] = releases

          # Fetch all commits for releases concurrently
          tasks = [
              fetch_commits_by_release(session, owner, repo_name, release.get("tag_name"))
              for release in releases if release.get("tag_name")
          ]

          print(f"🔍 Fetching commits for {len(tasks)} tag(s) in {full_name}...")
          commits_list = await asyncio.gather(*tasks)

          for release, commits in zip([r for r in releases if r.get("tag_name")], commits_list):
              release_commits[release["id"]] = commits

        simple_insert_to_db(repo, repo_releases, release_commits)
        print(f"✅ Saved {owner}/{repo_name}")

    await asyncio.gather(*[process_repo(repo) for repo in repos])

    end_time = time.time()
    print(f"⏱️ Time taken: {end_time - start_time:.2f} seconds")