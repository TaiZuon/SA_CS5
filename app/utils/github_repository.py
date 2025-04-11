from app.config.database import get_connection

def reset_db():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

    # Drop tables if they exist
    cursor.execute("DROP TABLE IF EXISTS commit;")
    cursor.execute("DROP TABLE IF EXISTS releases;")
    cursor.execute("DROP TABLE IF EXISTS repo;")

    # Create tables again
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repo (
            id INT AUTO_INCREMENT NOT NULL UNIQUE,
            user TEXT NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY (id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS releases (
            id INT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            repoID INT NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (repoID) REFERENCES repo(id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commit (
            hash TEXT NOT NULL,
            message TEXT NOT NULL,
            releaseID INT NOT NULL,
            FOREIGN KEY (releaseID) REFERENCES releases(id)
        );
    """)

    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    connection.commit()
    cursor.close()
    connection.close()


def save_to_db(repos, repo_releases, release_commits):
    connection = get_connection()
    cursor = connection.cursor()

    for repo in repos:
        cursor.execute(
            "INSERT INTO repo (id, user, name) VALUES (%s, %s, %s)",
            (repo["id"], repo["owner"]["login"], repo["name"])
        )

    for repo_id, releases in repo_releases.items():
        for release in releases:
            release_id = release["id"]
            content = release.get("body", "")[:65000]

            cursor.execute(
                "INSERT INTO releases (id, content, repoID) VALUES (%s, %s, %s)",
                (release_id, content, repo_id)
            )

            for commit in release_commits.get(release_id, []):
                cursor.execute(
                    "INSERT INTO commit (hash, message, releaseID) VALUES (%s, %s, %s)",
                    (commit["sha"], commit["commit"]["message"][:1000], release_id)
                )

    connection.commit()
    cursor.close()
    connection.close()