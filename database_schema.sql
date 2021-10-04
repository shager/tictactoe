DROP TABLE IF EXISTS players;
CREATE TABLE players (
	id    INTEGER PRIMARY KEY NOT NULL,
	name  VARCHAR(255) NOT NULL,
	score INTEGER NOT NULL,
	hash  VARCHAR(255) NOT NULL
);


DROP TABLE IF EXISTS games;
CREATE TABLE games (
	id          INTEGER PRIMARY KEY NOT NULL,
	player_1_id INTEGER NOT NULL,
	player_2_id INTEGER NOT NULL,
	turn        INTEGER NOT NULL,
	board       INTEGER NOT NULL
);
