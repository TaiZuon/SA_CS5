from main_app.config import SQL_DUMP_PATH
import os
import time

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
    PRIMARY KEY (`hash`, `releaseID`)  -- Composite Key
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

def write_schema_if_needed():
    timestamp = time.strftime("%Y%m%d_%H%M%S")  # Lấy thời gian đến giây
    sql_file = f"{SQL_DUMP_PATH}/dump_{timestamp}.sql"

    os.makedirs(os.path.dirname(sql_file), exist_ok=True)

    with open(sql_file, "w", encoding="utf-8") as f:
        f.write(CREATE_DB_AND_TABLES_SQL + "\n")

    return sql_file  # Nếu cần dùng file path để lưu các lệnh tiếp theo

