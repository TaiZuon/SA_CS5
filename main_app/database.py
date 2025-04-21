import pymysql
import logging
from main_app.config import DB_CONFIG

def connect_db():
    return pymysql.connect(**DB_CONFIG)

def reset_db():
    conn = connect_db()
    cursor = conn.cursor()
    try:
        logging.info("🔄 Resetting database...")
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        cursor.execute("TRUNCATE TABLE `commit`;")
        cursor.execute("TRUNCATE TABLE `release`;")
        cursor.execute("TRUNCATE TABLE `repo`;")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        conn.commit()
        logging.info("✅ Database reset complete.")
    except Exception as e:
        logging.error(f"❌ Lỗi khi reset database: {e}")
    finally:
        cursor.close()
        conn.close()

def save_repo(repo):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO `repo` (id, user, name) VALUES (%s, %s, %s)",
            (repo["id"], repo["owner"]["login"], repo["name"])
        )
        conn.commit()
        logging.info(f"✅ Saved repo: {repo['name']}")
    except Exception as e:
        logging.warning(f"⚠️ Lỗi khi lưu repo {repo['name']}: {e}")
    finally:
        cursor.close()
        conn.close()

def save_release(release, repo_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO `release` (id, content, repoID) VALUES (%s, %s, %s)",
            (release["id"], release.get("body", "")[:65000], repo_id)
        )
        conn.commit()
        logging.info(f"✅ Saved release: {release.get('tag_name', 'unknown')} for repoID: {repo_id}")
    except Exception as e:
        logging.warning(f"⚠️ Lỗi khi lưu release {release.get('tag_name', '')}: {e}")
    finally:
        cursor.close()
        conn.close()

def save_commit(commit, release_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO `commit` (hash, message, releaseID) VALUES (%s, %s, %s)",
            (commit["sha"], commit["commit"]["message"][:1000], release_id)
        )
        conn.commit()
        logging.info(f"✅ Saved commit: {commit['sha']} for releaseID: {release_id}")
    except Exception as e:
        logging.warning(f"⚠️ Lỗi khi lưu commit {commit['sha']}: {e}")
    finally:
        cursor.close()
        conn.close()

def save_commits_batch(commits, release_id):
    if not commits:
        return

    conn = connect_db()
    cursor = conn.cursor()
    try:
        commit_data = []
        for commit in commits:
            sha = commit["sha"]
            message = commit["commit"]["message"][:1000]
            commit_data.append((sha, message, release_id))

        cursor.executemany(
            "INSERT INTO `commit` (hash, message, releaseID) VALUES (%s, %s, %s)",
            commit_data
        )
        conn.commit()
    except Exception as e:
        logging.warning(f"⚠️ Lỗi khi batch insert commit release {release_id}: {e}")
    finally:
        cursor.close()
        conn.close()

def delete_release(release_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        logging.info(f"🗑️ Đang xoá release {release_id} và các commit liên quan...")

        # Xoá commit trước
        cursor.execute("DELETE FROM `commit` WHERE releaseID = %s", (release_id,))
        logging.info(f"🧹 Đã xoá commit liên quan đến release {release_id}")

        # Xoá release
        cursor.execute("DELETE FROM `release` WHERE id = %s", (release_id,))
        conn.commit()

        logging.info(f"✅ Release {release_id} đã được xoá khỏi DB")
    except Exception as e:
        conn.rollback()
        logging.warning(f"❌ Lỗi khi xoá release {release_id}: {e}")
    finally:
        cursor.close()
        conn.close()

