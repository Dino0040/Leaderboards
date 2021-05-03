# syntax=docker/dockerfile:1
FROM python:buster

EXPOSE 8000/tcp

WORKDIR /usr/src/app
VOLUME /usr/src/app/database

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install sqlite3
RUN pip install fastapi requests uvicorn

COPY leaderboards.sql run.sh main.py ./

RUN chmod +x ./run.sh

CMD ./run.sh
