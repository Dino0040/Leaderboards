PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE "ban" ("itch_user_id" INTEGER PRIMARY KEY, "ban_reason" TEXT NOT NULL);
CREATE TABLE "leaderboard" ( "id" INTEGER PRIMARY KEY, "secret" TEXT NOT NULL, "itch_user_id" INTEGER NOT NULL, "name" TEXT, "sorting" TEXT DEFAULT "d");
CREATE TABLE "entry" ( "name" TEXT NOT NULL, "value" NUMERIC NOT NULL, "leaderboard_id" INTEGER NOT NULL, FOREIGN KEY ("leaderboard_id") REFERENCES leaderboard ("id"), PRIMARY KEY("name", "leaderboard_id"));
COMMIT;
