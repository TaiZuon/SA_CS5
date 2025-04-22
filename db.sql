CREATE DATABASE IF NOT EXISTS `github_data` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE `github_data`;

CREATE TABLE IF NOT EXISTS `repo` (
	`id` int NOT NULL UNIQUE,
	`user` text NOT NULL,
	`name` text NOT NULL,
	PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `release` (
	`id` int NOT NULL UNIQUE,
	`content` text NOT NULL,
	`repoID` int NOT NULL,
	PRIMARY KEY (`id`, `repoID`)
);

CREATE TABLE IF NOT EXISTS `commit` (
    `hash` VARCHAR(64) NOT NULL,
    `message` text NOT NULL,
    `releaseID` int NOT NULL,
    PRIMARY KEY (`hash`, `releaseID`)  -- Composite Key
);

ALTER TABLE `release` 
    ADD CONSTRAINT `release_fk0` 
    FOREIGN KEY (`repoID`) 
    REFERENCES `repo`(`id`);

ALTER TABLE `commit` 
    ADD CONSTRAINT `commit_fk2` 
    FOREIGN KEY (`releaseID`) 
    REFERENCES `release`(`id`);
