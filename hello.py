import aiohttp
import asyncio
import pymysql
import os
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {TOKEN}"
}

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "github_data"
}

def connect_db():
    return pymysql.connect(**DB_CONFIG)

def reset_db():
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
    cursor.execute("TRUNCATE TABLE commit;")
    cursor.execute("TRUNCATE TABLE releases;")
    cursor.execute("TRUNCATE TABLE repo;")
    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database đã được reset!")

async def fetch_top_repos(session, per_page=50):
    url = f"https://api.github.com/search/repositories?q=stars:>1000&sort=stars&per_page={per_page}&page=1"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        return data.get("items", [])

async def fetch_releases(session, owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        return data if isinstance(data, list) else []

async def fetch_commits_by_release(session, owner, repo, tag_name):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={tag_name}&per_page=10"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        return data if isinstance(data, list) else []

def save_to_db(repos, repo_releases, release_commits):
    conn = connect_db()
    cursor = conn.cursor()

    for repo in repos:
        cursor.execute("INSERT INTO repo (id, user, name) VALUES (%s, %s, %s)",
                       (repo["id"], repo["owner"]["login"], repo["name"]))

    for repo_id, releases in repo_releases.items():
        for release in releases:
            release_id = release["id"]
            tag_name = release["tag_name"]
            content = release.get("body", "")[:65000]
            cursor.execute("INSERT INTO releases (id, content, repoID) VALUES (%s, %s, %s)", 
                        (release_id, content, repo_id))

            if release_id in release_commits:
                for commit in release_commits[release_id]:
                    cursor.execute("INSERT INTO commit (hash, message, releaseID) VALUES (%s, %s, %s)",
                                   (commit["sha"], commit["commit"]["message"][:1000], release_id))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Dữ liệu đã lưu vào database!")

async def main():
    async with aiohttp.ClientSession() as session:
        repos = await fetch_top_repos(session, per_page=50)
        
        repo_releases = {}
        release_commits = {}

        for repo in repos:
            owner, repo_name = repo["owner"]["login"], repo["name"]
            releases = await fetch_releases(session, owner, repo_name)
            
            if releases:
                repo_releases[repo["id"]] = releases
                
                for release in releases:
                    tag_name = release["tag_name"]
                    commits = await fetch_commits_by_release(session, owner, repo_name, tag_name)
                    release_commits[release["id"]] = commits
        
        reset_db()
        save_to_db(repos, repo_releases, release_commits)

asyncio.run(main())
