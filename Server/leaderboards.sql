PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE leaderboard ( "id" INTEGER PRIMARY KEY, "secret" TEXT NOT NULL, "owner" INTEGER NOT NULL, "name" TEXT);
CREATE TABLE IF NOT EXISTS "entry" ( "name" TEXT NOT NULL, "value" NUMERIC NOT NULL, "leaderboard" INTEGER NOT NULL, time INTEGER NOT NULL DEFAULT 0, FOREIGN KEY ("leaderboard") REFERENCES leaderboard ("id"), PRIMARY KEY("name", "leaderboard"));
COMMIT;
