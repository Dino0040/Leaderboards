#!/bin/bash
if ! test -e "./database/leaderboards.db"; then
    sqlite3 ./database/leaderboards.db '.read leaderboards.sql'
fi
uvicorn --host 0.0.0.0 --port 8000 main:app
