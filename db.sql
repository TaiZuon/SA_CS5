CREATE TABLE IF NOT EXISTS `release` (
	`id` int NOT NULL UNIQUE,
	`content` text NOT NULL,
	`repoID` int NOT NULL,
	PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `repo` (
	`id` int AUTO_INCREMENT NOT NULL UNIQUE,
	`user` text NOT NULL,
	`name` text NOT NULL,
	PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `commit` (
	`hash` text NOT NULL,
	`message` text NOT NULL,
	`releaseID` int NOT NULL
);


ALTER TABLE `release` ADD CONSTRAINT `fk_release_repo` FOREIGN KEY (`repoID`) REFERENCES `repo`(`id`);
ALTER TABLE `commit` ADD CONSTRAINT `fk_commit_release` FOREIGN KEY (`releaseID`) REFERENCES `release`(`id`);