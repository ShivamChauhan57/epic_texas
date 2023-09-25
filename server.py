import http.server
from socketserver import ThreadingMixIn
import socketserver
import time
import json
import sys
import sqlite3
import inspect
from pathlib import Path
import jwt

from request_handlers import get_requests, post_requests

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

def handle_request(self, request_type):
    request_handler = {**get_requests, **post_requests}.get(self.path)
    if request_handler == None:
        self.send_error(404)
        return

    kwargs = dict()
    if request_type == 'post':
        content_length = int(self.headers['Content-Length'])
        raw_data = self.rfile.read(content_length)
        kwargs['data'] = json.loads(raw_data)

    if 'user' in inspect.signature(request_handler).parameters:
        try:
            assert self.headers['Authorization']
            token = self.headers['Authorization'].strip().split(' ')[1]
            payload = jwt.decode(token, Path('./jwt-key.txt').read_text().strip(), algorithms=['HS256'])
            kwargs['user'] = (payload['user_id'], payload['username'])
        except (AssertionError, IndexError, jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            self.send_error(401)
            return

    with sqlite3.connect('users.db') as conn:
        response, status = request_handler(conn, **kwargs)

    response = json.dumps(response)

    self.send_response(status)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', len(response))
    self.end_headers()
    self.wfile.write(response.encode())

class ThreadedHTTPServer(ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    do_GET = lambda self: handle_request(self, 'get')
    do_POST = lambda self: handle_request(self, 'post')

if __name__ == '__main__':
    with ThreadedHTTPServer(('0.0.0.0', PORT), MyRequestHandler) as httpd:
        print(f'Serving on port {PORT}')
        httpd.serve_forever()
