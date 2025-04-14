from app.config.database import get_connection

# Insert a single repository, its releases, and their commits into the database.
# Assumes `repo` is a dictionary with "user" and "name" keys.
def simple_insert_to_db(repo, repo_releases, release_commits):
    print(f"[📥] Inserting repo: {repo['user']}/{repo['name']}")

    # Establish a connection to the database
    connection = get_connection()
    cursor = connection.cursor()

    # Temporarily disable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

    # Build unique key for repo
    key = f"{repo['user']}/{repo['name']}"

    # Insert the repository
    cursor.execute(
        "INSERT INTO repo (user, name) VALUES (%s, %s)",
        (repo["user"], repo["name"])
    )
    repo_id = cursor.lastrowid
    print(f"  ✅ Repo inserted with ID: {repo_id}")

    # Insert releases and corresponding commits
    for release in repo_releases.get(key, []):
        release_id = release["id"]
        content = release.get("body", "")[:65000]

        cursor.execute(
            "INSERT INTO releases (id, content, repoID) VALUES (%s, %s, %s)",
            (release_id, content, repo_id)
        )
        print(f"    📦 Inserted release: {release_id}")

        for commit in release_commits.get(release_id, []):
            commit_hash = commit["sha"]
            message = commit["commit"]["message"][:1000]

            cursor.execute(
                "INSERT INTO commit (hash, message, releaseID) VALUES (%s, %s, %s)",
                (commit_hash, message, release_id)
            )
            print(f"      🔧 Inserted commit: {commit_hash[:7]}")

    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

    # Commit and close
    connection.commit()
    cursor.close()
    connection.close()
    print(f"[✅] Done inserting {repo['user']}/{repo['name']}\n")


# Efficiently insert repositories, releases, and commits into the database using batch operations.
# Uses `executemany` to perform batch inserts for higher performance.
# Reduces round-trips to the database, improving insert throughput.
def batch_save_to_db(repo, repo_releases, release_commits):
    print(f"[📥] Batch saving repo: {repo['user']}/{repo['name']}")

    # Establish a connection to the database
    connection = get_connection()
    cursor = connection.cursor()

    # Disable foreign key checks temporarily
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

    # Insert the single repo
    cursor.execute("INSERT INTO repo (user, name) VALUES (%s, %s)", (repo["user"], repo["name"]))
    connection.commit()

    # Get the repo ID
    cursor.execute("SELECT id FROM repo WHERE user = %s AND name = %s ORDER BY id DESC LIMIT 1", (repo["user"], repo["name"]))
    result = cursor.fetchone()
    if result is None:
        print("❌ Failed to fetch inserted repo ID.")
        return
    repo_id = result[0]
    print(f"  ✅ Repo inserted with ID: {repo_id}")

    # Build release and commit insert values
    key = f"{repo['user']}/{repo['name']}"
    release_values = []
    commit_values = []

    for release in repo_releases.get(key, []):
        release_id = release["id"]
        content = release.get("body", "")[:65000]
        release_values.append((release_id, content, repo_id))
        print(f"    📦 Prepared release: {release_id}")

        for commit in release_commits.get(release_id, []):
            commit_values.append((commit["sha"], commit["commit"]["message"][:1000], release_id))

    # Batch insert releases
    if release_values:
        cursor.executemany("INSERT INTO releases (id, content, repoID) VALUES (%s, %s, %s)", release_values)
        print(f"  ✅ Inserted {len(release_values)} releases")

    # Batch insert commits
    if commit_values:
        cursor.executemany("INSERT INTO commit (hash, message, releaseID) VALUES (%s, %s, %s)", commit_values)
        print(f"  ✅ Inserted {len(commit_values)} commits")

    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    connection.commit()
    cursor.close()
    connection.close()
    print(f"[✅] Done saving {repo['user']}/{repo['name']}\n")