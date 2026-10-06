"""Dependency-free threaded HTTP adapter. Never log bodies, tokens or exports."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from errors import APIError, fail
from json_value import loads
from service import Service

service = Service()


class Handler(BaseHTTPRequestHandler):
    server_version = "Stage1"
    sys_version = ""

    def log_message(self, *_):
        pass

    def send_error(self, code, message=None, explain=None):
        # Include JSON errors for HTTP parser failures and unsupported methods too.
        status = 404 if code in (501, 505) else (400 if code >= 500 else code)
        error = "not_found" if status == 404 else "malformed_request"
        self.respond(status, {"error": {"code": error, "message": error.replace("_", " ")}})

    def read_body(self):
        try:
            length = self.headers.get("Content-Length", "0")
            if not length.isascii() or not length.isdecimal():
                fail(400, "malformed_request")
            raw = self.rfile.read(int(length))
            body = loads(raw.decode("utf-8"))
            if not isinstance(body, dict):
                fail(400, "malformed_request")
            return body
        except (ValueError, UnicodeError, RecursionError, OverflowError):
            fail(400, "malformed_request")

    def respond(self, status, body):
        data = b"" if body is None else json.dumps(body, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        if data:
            self.wfile.write(data)

    def handle_api(self):
        try:
            status, body = service.dispatch(self.command, self.path, self.headers.get("Authorization"), self.headers.get("Idempotency-Key"), self.read_body)
            self.respond(status, body)
        except APIError as exc:
            self.respond(exc.status, {"error": {"code": exc.code, "message": exc.code.replace("_", " ")}})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return
        except Exception as exc:
            # Last defense against hostile malformed input, without exposing it.
            print("Rejected request: " + type(exc).__name__, file=sys.stderr)
            self.respond(400, {"error": {"code": "malformed_request", "message": "Invalid request"}})

    do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = do_HEAD = do_OPTIONS = do_TRACE = handle_api


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


if __name__ == "__main__":
    sys.set_int_max_str_digits(0)
    Server(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
