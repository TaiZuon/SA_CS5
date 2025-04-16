import asyncio
import random
import time
from app.utils.tor.py import create_tor_session, get_next_token
from app.utils.write_database.insert_methods import simple_insert_to_db, batch_save_to_db
from app.utils.write_database.reset_db import reset_db
from bs4 import BeautifulSoup


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

# Fetch releases of a repository
async def fetch_releases(session, owner, repo, token):
    releases = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100&page={page}"
        headers = {'Authorization': f'token {token}'}
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            await asyncio.sleep(random.uniform(1, 5))

            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining == '0':
                reset_time = int(resp.headers.get("X-RateLimit-Reset", time.time()))
                wait_time = reset_time - int(time.time()) + 5
                print(f"[⛔] {token} Rate limit reached, waiting for {wait_time} seconds...",)
                await asyncio.sleep(wait_time)
                continue

            if len(data) == 0:
                break
        releases.extend(data)
        page += 1
    
    return releases

# Fetch commits between two release tags using GitHub Compare API
async def fetch_commits_by_release(session, owner, repo, base_tag, head_tag, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base_tag}...{head_tag}"
    headers = {'Authorization': f'token {token}'}

    async with session.get(url, headers=headers) as resp:
        data = await resp.json()
        await asyncio.sleep(random.uniform(1, 3))

        if 'commits' in data:
            return data['commits']
        else:
            print(f"[⚠️] Failed to fetch commits for {owner}/{repo} from {base_tag} to {head_tag}")
            return []

# Main function to fetch top repositories, their releases, and corresponding commits,
# then reset the database and store all fetched data
# Main function to fetch data and store it
# Main function to fetch data and store it
async def fetch_and_store_data(total_pages=50):

    async with await create_tor_session() as session:  # Automatically closes the session
        repos = await fetch_top_repos(session, total_pages)

        reset_db()
        start_time = time.time()

        async def process_repo(repo):
            owner, repo_name = repo["user"], repo["name"]

            token = token = get_next_token()

            async with semaphore:
                releases = await fetch_releases(session, owner, repo_name, token)
                print(f"🔁 Found {len(releases)} releases for {owner}/{repo_name}")

                repo_releases = {}
                release_commits = {}

                if len(releases) >= 2:
                    # Save the list of releases for the repo
                    repo_releases[f"{owner}/{repo_name}"] = releases

                    # Sort releases chronologically based on creation time
                    sorted_releases = sorted(
                        [r for r in releases if r.get("tag_name")],
                        key=lambda r: r["created_at"]
                    )

                    tasks = []
                    tag_pairs = []

                    # Create tasks to compare commits between consecutive releases
                    for i in range(1, len(sorted_releases)):
                        base_tag = sorted_releases[i - 1]["tag_name"]
                        head_tag = sorted_releases[i]["tag_name"]
                        tag_pairs.append((sorted_releases[i]["id"], base_tag, head_tag))
                        tasks.append(fetch_commits_by_release(session, owner, repo_name, base_tag, head_tag, token))

                    # Run all comparison tasks concurrently
                    commits_list = await asyncio.gather(*tasks)

                    # Store commits for each release (based on head release's ID)
                    for (release_id, base_tag, head_tag), commits in zip(tag_pairs, commits_list):
                        release_commits[release_id] = commits

                elif len(releases) == 1:
                    # Only one release — can't compare, but still save the release
                    repo_releases[f"{owner}/{repo_name}"] = releases
                    print(f"[⚠️] Only one release for {owner}/{repo_name}, skipping commit comparison.")

                # Save everything to the database
                batch_save_to_db(repo, repo_releases, release_commits)
                print(f"✅ Saved {owner}/{repo_name}")

        # Process all repositories concurrently
        await asyncio.gather(*[process_repo(repo) for repo in repos])
        end_time = time.time()
        print(f"⏱️ Time taken: {end_time - start_time:.2f} seconds")