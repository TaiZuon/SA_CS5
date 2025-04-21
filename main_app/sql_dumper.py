import os
import time
import asyncio
from main_app.config import SQL_DUMP_PATH

# Nội dung tạo DB và các bảng
CREATE_DB_AND_TABLES_SQL = """
-- Tạo database nếu chưa có
CREATE DATABASE IF NOT EXISTS github_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE github_data;

-- Tạo bảng repo
CREATE TABLE IF NOT EXISTS `repo` (
    `id` INT NOT NULL UNIQUE,
    `user` TEXT NOT NULL,
    `name` TEXT NOT NULL,
    PRIMARY KEY (`id`)
);

-- Tạo bảng release
CREATE TABLE IF NOT EXISTS `release` (
    `id` INT NOT NULL UNIQUE,
    `content` TEXT NOT NULL,
    `repoID` INT NOT NULL,
    PRIMARY KEY (`id`, `repoID`)
);

-- Tạo bảng commit
CREATE TABLE IF NOT EXISTS `commit` (
    `hash` VARCHAR(64) NOT NULL,
    `message` TEXT NOT NULL,
    `releaseID` INT NOT NULL,
    PRIMARY KEY (`hash`, `releaseID`)
);

-- Thêm khóa ngoại
ALTER TABLE `release`
    ADD CONSTRAINT `release_fk0`
    FOREIGN KEY (`repoID`)
    REFERENCES `repo`(`id`);

ALTER TABLE `commit`
    ADD CONSTRAINT `commit_fk2`
    FOREIGN KEY (`releaseID`)
    REFERENCES `release`(`id`);

-- Tắt kiểm tra khóa ngoại trước khi insert
SET FOREIGN_KEY_CHECKS=0;
"""

# Lock để tránh race condition khi ghi file
file_write_lock = asyncio.Lock()

# Tạo file dump theo thời điểm chương trình chạy (duy nhất)
RUN_TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")
SQL_FILE_PATH = os.path.join(SQL_DUMP_PATH, f"dump_{RUN_TIMESTAMP}.sql")

# Tạo thư mục và file nếu chưa có
os.makedirs(SQL_DUMP_PATH, exist_ok=True)
with open(SQL_FILE_PATH, "w", encoding="utf-8") as f:
    f.write(CREATE_DB_AND_TABLES_SQL + "\n")

print(f"💾 Dump SQL file created: {SQL_FILE_PATH}")

# Hàm ghi từng lệnh SQL vào file (có lock)
async def _append_sql(statement: str):
    async with file_write_lock:
        with open(SQL_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(statement.strip() + ";\n")

# Hàm ghi repo
async def save_repo_sql(repo):
    statement = (
        f'INSERT INTO `repo` (id, user, name) '
        f'VALUES ({repo["id"]}, "{repo["owner"]["login"]}", "{repo["name"]}")'
    )
    await _append_sql(statement)

# Hàm ghi release
async def save_release_sql(release, repo_id):
    content = release.get("body", "").replace('"', '\\"').replace("\n", " ")[:65000]
    statement = (
        f'INSERT INTO `release` (id, content, repoID) '
        f'VALUES ({release["id"]}, "{content}", {repo_id})'
    )
    await _append_sql(statement)

# Hàm ghi commit
async def save_commits_sql(commits, release_id):
    for commit in commits:
        message = commit["commit"]["message"].replace('"', '\\"').replace("\n", " ")[:1000]
        statement = (
            f'INSERT INTO `commit` (hash, message, releaseID) '
            f'VALUES ("{commit["sha"]}", "{message}", {release_id})'
        )
        await _append_sql(statement)
