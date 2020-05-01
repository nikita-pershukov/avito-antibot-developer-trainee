# Avito antibot developer trainee

This is solution for tesk task with http-service and rate limit

## Installing

Install docker and docker-compose and git

```
apt install docker docker-compose git
```

Clone this repo

```
git clone https://github.com/nikita-pershukov/avito-antibot-developer-trainee
```

Build docker image

```
docker-compose build
```

## Starting

Start docker container

```
docker-compose up
```

Try to connect to server

```
echo -e "GET / HTTP/1.1\nX-Forwarded-For: 123.123.123.123\n" | nc 127.0.0.1 8080
```
