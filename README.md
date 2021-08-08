## About

This repo contains all that is needed to host and use a server providing leaderboards for games.

## Using the free leaderboard server

If all you want is a free leaderboard in your application download one of the client implementations for your game engine and log in using itch.io on [this page](https://exploitavoid.com/leaderboards/v1/) to create and manage your leaderboards.

*DISCLAMER: I will use the public server myself for future jam games so have the intention to keep it up for as long as I can with as few outages as possible, but there are no guarantees. To prevent abuse the MAX_\* rate limits defined in the main.py of the repo are in place - be nice!*

## Hosting a leaderboard server yourself using docker

**Create the leaderboard container in the /Server folder:**

`docker build -t leaderboard .`

**Start the leaderboard container with port 80 exposed to the host (We will connect the webinterface to the same network):**

`docker run -d -p 80:80 --name leaderboard leaderboard`

**Modify the OAuth link and page title:**

The OAUTHLINK in /Client/Webinterface/config.js has to be changed to one you generate yourself using [their site](https://itch.io/user/settings/oauth-apps).

Change the PAGETITLE in the same file.

**Create the webinterface container in the /Client/Webinterface folder:**

`docker build -t webinterface .`

**Start the webinterface container connected to the network of the leaderboard container):**

`docker run -d --network container:leaderboard --name webinterface webinterface`


Your webinterface is now available at http://<span></span>127.0.0.1/leaderboards/v1/ and the server at http://<span></span>127.0.0.1/leaderboards/v1/api of the host
