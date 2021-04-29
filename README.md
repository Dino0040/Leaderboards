## About

This repo contains all that is needed to host and use a server to provide leaderboards in games.

## Using the free leaderboard server

If all you want is a free leaderboard in your application download one of the client implementations for your game engine and log in using itch.io on [this page](https://exploitavoid.com/leaderboards/) to create and manage your leaderboards.

## Hosting a leaderboard server yourself

**Install the required packages using your package manager:**

`apt install sqlite3 python3 python3-pip`

**Create the database file:**

`sqlite3 autction.db '.read create.sql'`

**Install the python packages required for the server using pip:**

`pip install fastapi requests uvicorn`

(You can replace uvicorn with any other ASGI server)

**Start the server:**

`uvicorn main:app`

**Host the webinterface Clients/index.html using any webserver**

The itch OAuth link in the index.html has to be changed to one you generate yourself using [their site](https://itch.io/user/settings/oauth-apps).

Your webserver also has to redirect urls in the form of your.domain/api to the uvicorn server.


(Todo: Make hosting own webinterface easier - Docker?)