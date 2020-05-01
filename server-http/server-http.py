#!/usr/bin/env python3

MAX_LINE = 64*1024
MAX_HEADERS = 64*1024

import socket
import sys
from email.parser import Parser
from functools import lru_cache
from urllib.parse import parse_qs, urlparse
import ipaddress
from datetime import datetime
import time

class Request:
    def __init__(self, method, target, version, headers, rfile):
        self._method = method
        self._target = target
        self._version = version
        self._headers = headers
        self._rfile = rfile

    def path(self):
        return self.url.path

    def query(self):
        return parse_qs(self.url.query)

    def url(self):
        return urlparse(self.target)

class Response:
    def __init__(self, status, reason, headers=None, body=None):
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body

class MyHTTPServer:
    def __init__(self, host, port, mask, delta, delay, limit):
        self._host = host
        self._port = port
        self._serv_sock = 0
        self._logs = {}
        self._mask = mask
        self._delta = delta
        self._delay = delay
        self._limit = limit

    def serve_forever(self):
        self._serv_sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
            proto=0)

        try:
            self._serv_sock.bind((self._host, self._port))
        except socket.gaierror:
            print("Cannot bind socket")
        else:
            self._serv_sock.listen()

            while True:
                conn, addr = self._serv_sock.accept()
                print("Connected:", addr)
                self.serve_client(conn, addr)

    def serve_client(self, conn, addr):
        try:
            seconds = int(time.mktime(time.localtime()))
            req = self.parse_request(conn)
            try:
                resp, net = self.handle_request(req, addr, seconds)
            except ValueError as e:
                print("Cannot handle request:", e)
            else:
                self.send_response(conn, resp, seconds, net)
                conn.close()
        except ConnectionError as e:
            print("Connections Erorr:", e)

    def parse_request(self, conn):
        rfile = conn.makefile("rb")
        try:
            method, target, ver = self.parse_request_line(rfile)
        except ValueError as e:
            print("Cannot parse request line: ", e)
        try:
            headers = self.parse_headers(rfile)
        except ValueError as e:
            print("Cannot parse headers:", e)
        return Request(method, target, ver, headers, rfile)

    def parse_request_line(self, rfile):
        raw = rfile.readline(MAX_LINE + 1)
        if len(raw) > MAX_LINE:
            raise ValueError("Request line is too long")

        req_line = str(raw, "iso-8859-1")
        req_line = req_line.rstrip("\n")
        words = req_line.split()
        if len(words) != 3:
            raise ValueError("Malformed request line")

        method, target, ver = words
        if ver != "HTTP/1.1":
            raise ValueError("Unexpected HTTP version")

        return words

    def parse_headers(self, rfile):
        headers = []
        while True:
            raw = rfile.readline(MAX_LINE + 1)
            if len(raw) > MAX_LINE:
                raise ValueError("Header line is too long: " + raw[:30].decode("iso-8859-1") + "...")
            if raw in (b"\r\n", b"\n" b""):
                break

            headers.append(raw)
            if len(headers) > MAX_HEADERS:
                raise ValueError("Too many headers")

        sheaders = b''.join(headers).decode("iso-8859-1")
        return Parser().parsestr(sheaders)

    def handle_request(self, req, addr, seconds):
        ip = req._headers["X-Forwarded-For"]
        if ip is None:
            raise ValueError("No ip found")
        net = str(ipaddress.IPv4Interface(ip+"/"+str(self._mask)).network)
        self.add_log(net, seconds)
        code, message = self.check_limit(net, seconds)
        print("Response to:", addr, "-", code, message)
        return (Response(code, message), net)

    def add_log(self, net, seconds):
        if net not in self._logs:
            self._logs[net] = {}
        if seconds not in self._logs[net]:
            self._logs[net][seconds] = 1
        else:
            self._logs[net][seconds] += 1

    def check_limit(self, net, seconds):
        if "ban" in self._logs[net]:
            if seconds > self._logs[net]["ban"] + delay:
                return self.count_connections(net, seconds)
            else:
                return (429, "Too Many Requests")
        else:
            return self.count_connections(net, seconds)

    def count_connections(self, net, seconds):
        count = 0
        to_delete = []
        for k, v in self._logs[net].items():
            if k.__class__ is int:
                if k in range(seconds - self._delta, seconds + 1):
                    count += v
                else:
                    to_delete.append(int(k))
        for i in to_delete:
            self._logs[net].pop(i)
        if count > self._limit:
            self._logs[net]["ban"] = seconds
            print("Banned:", net)
            return (429, "Too Many Requests")
        else:
            return (200, "OK")

    def send_response(self, conn, resp, seconds, net):
        wfile = conn.makefile("wb")
        status_line = "HTTP/1.1 " + str(resp.status) + " " + resp.reason + "\n"
        wfile.write(status_line.encode("iso-8859-1"))
        content_line = "Content-Type: text/html\n"
        wfile.write(content_line.encode("iso-8859-1"))
        if resp.status == 429:
            retry_line = "Retry-After: " + str(self._delay-(seconds - self._logs[net]["ban"])) + "\n"
            wfile.write(retry_line.encode("iso-8859-1"))

        wfile.write(b"\n")

        with open(str(resp.status)+".html") as f:
            html = f.read()
        for line in html.split("\n"):
            line = line.replace("$limit$", str(self._limit))
            line = line.replace("$delta$", str(self._delta))
            line = line.replace("$mask$", str(self._mask))
            wfile.write(line.encode("iso-8859-1"))
            wfile.write(b"\n")

        wfile.flush()
        wfile.close()

    def close(self):
        self._serv_sock.close()

if __name__ == "__main__":
    host = sys.argv[1]
    try:
        port = int(sys.argv[2])
        mask = int(sys.argv[3])
        delta = int(sys.argv[4])
        delay = int(sys.argv[5])
        limit = int(sys.argv[6])
    except ValueError as e:
        print("Wrong args:", e)
        exit(1)

    serv = MyHTTPServer(host, port, mask, delta, delay, limit)
    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serv.close()
