FROM alpine:3.11.6

ENV PYTHON_VERSION 3.8.2-r0

RUN apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/v3.11/main python3=${PYTHON_VERSION}

COPY . /opt/

WORKDIR /opt/server-http

ENTRYPOINT ["/opt/server-http/start-server.sh"]
