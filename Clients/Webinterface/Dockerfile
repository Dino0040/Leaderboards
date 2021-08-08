# syntax=docker/dockerfile:1
FROM debian:buster

EXPOSE 80/tcp

WORKDIR /usr/src/app

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install lighttpd

COPY lighttpd.conf ./
COPY index.html config.js loading.png ./html/leaderboards/v1/

CMD lighttpd-angel -D -f /usr/src/app/lighttpd.conf
