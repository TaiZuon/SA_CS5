import aiohttp
import asyncio
import pymysql
import os
from dotenv import load_dotenv
import logging

# Load biến môi trường
load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {TOKEN}"
}

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "tva",
    "database": "CS5"
}

def connect_db():
    logging.info("Kết nối đến cơ sở dữ liệu...")
    return pymysql.connect(**DB_CONFIG)

def reset_db():
    logging.info("Đang reset database...")
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        logging.info("Đã tắt kiểm tra khóa ngoại.")
        cursor.execute("TRUNCATE TABLE `commit`;")
        logging.info("Đã xóa dữ liệu trong bảng `commit`.")
        cursor.execute("TRUNCATE TABLE `release`;")
        logging.info("Đã xóa dữ liệu trong bảng `release`.")
        cursor.execute("TRUNCATE TABLE `repo`;")
        logging.info("Đã xóa dữ liệu trong bảng `repo`.")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        logging.info("Đã bật lại kiểm tra khóa ngoại.")
        conn.commit()
        logging.info("✅ Database đã được reset!")
    except Exception as e:
        logging.error(f"Lỗi khi reset database: {e}")
    finally:
        cursor.close()
        conn.close()

async def fetch_top_repos(session, per_page=50):
    logging.info("Đang fetch danh sách top repositories từ GitHub...")
    url = f"https://api.github.com/search/repositories?q=stars:>00&sort=stars&per_page={per_page}&page=1"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        logging.info(f"Đã fetch được {len(data.get('items', []))} repositories.")
        return data.get("items", [])

async def fetch_releases(session, owner, repo):
    logging.info(f"Đang fetch releases cho repository: {owner}/{repo}...")
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        logging.info(f"Đã fetch được {len(data) if isinstance(data, list) else 0} releases.")
        return data if isinstance(data, list) else []

async def fetch_commits_by_release(session, owner, repo, tag_name):
    logging.info(f"Đang fetch commits cho release: {tag_name} trong repository: {owner}/{repo}...")
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={tag_name}&per_page=10"
    async with session.get(url, headers=HEADERS) as response:
        data = await response.json()
        logging.info(f"Đã fetch được {len(data) if isinstance(data, list) else 0} commits.")
        return data if isinstance(data, list) else []

def save_to_db(repos, repo_releases, release_commits):
    logging.info("Đang lưu dữ liệu vào database...")
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Tắt ràng buộc khóa ngoại
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        logging.info("Đã tắt kiểm tra khóa ngoại.")

        # Lưu dữ liệu vào bảng `release` trước
        for repo_id, releases in repo_releases.items():
            for release in releases:
                release_id = release["id"]
                tag_name = release["tag_name"]
                content = release.get("body", "")[:65000]
                logging.info(f"Lưu release: {tag_name} cho repository ID: {repo_id}...")
                cursor.execute(
                    "INSERT INTO `release` (id, content, repoID) VALUES (%s, %s, %s)",
                    (release_id, content, repo_id)
                )

        # Lưu dữ liệu vào bảng `repo` sau
        for repo in repos:
            logging.info(f"Lưu repository: {repo['name']}...")
            cursor.execute(
                "INSERT INTO `repo` (id, user, name) VALUES (%s, %s, %s)",
                (repo["id"], repo["owner"]["login"], repo["name"])
            )

        # Lưu dữ liệu vào bảng `commit`
        for repo_id, releases in repo_releases.items():
            for release in releases:
                release_id = release["id"]
                if release_id in release_commits:
                    for commit in release_commits[release_id]:
                        logging.info(f"Lưu commit: {commit['sha']} cho release ID: {release_id}...")
                        cursor.execute(
                            "INSERT INTO `commit` (hash, message, releaseID) VALUES (%s, %s, %s)",
                            (commit["sha"], commit["commit"]["message"][:1000], release_id)
                        )

        conn.commit()
        logging.info("✅ Dữ liệu đã lưu vào database!")

    except Exception as e:
        logging.error(f"Lỗi khi lưu dữ liệu vào database: {e}")

    finally:
        # Bật lại ràng buộc khóa ngoại
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        logging.info("Đã bật lại kiểm tra khóa ngoại.")
        cursor.close()
        conn.close()

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