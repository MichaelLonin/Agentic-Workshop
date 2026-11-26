"""HTTP API for the repository registry, using only the Python standard library.

Run it:
    python -m app.server              # http://localhost:8000
    python -m app.server --port 8080
    python -m app.server --reset      # throw away saved data, start from the seed data

Data is saved in data/registry.json (change it with --data), so it survives a restart.

Who is calling: send the header "X-User: <username>". Without it you are "alice".

To add an endpoint:
    1. put the logic in app/service.py;
    2. add a small handler below with the @route decorator.
"""

import argparse
import json
import re
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from . import service
from .store import DataFileError, Store

DEFAULT_USER = "alice"
ROUTES = []

# Largest request body the server reads (TASK-001 security review). Bigger ones get 413 unread.
MAX_BODY = 64 * 1024


class BodyError(Exception):
    """A request body the server refuses to read. Carries the HTTP status to answer with."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def route(method, pattern):
    """Register a handler. Groups in the pattern become extra arguments."""

    def register(func):
        ROUTES.append((method, re.compile(f"^{pattern}$"), func))
        return func

    return register


class Request:
    """What a handler gets: the store, the caller, the query string and the JSON body."""

    def __init__(self, store, user, query, body):
        self.store = store
        self.user = user
        self.query = query
        self.body = body


# --- Endpoints -----------------------------------------------------------------


@route("GET", "/health")
def health(req):
    return 200, {"status": "ok"}


@route("GET", "/repositories")
def list_repositories(req):
    return 200, service.list_repositories(req.store, req.user)


@route("POST", "/repositories")
def register_repository(req):
    return 201, service.register_repository(req.store, req.user, req.body)


@route("GET", r"/repositories/(\d+)")
def get_repository(req, repository_id):
    return 200, service.get_repository(req.store, req.user, int(repository_id))


@route("DELETE", r"/repositories/(\d+)")
def remove_repository(req, repository_id):
    service.remove_repository(req.store, req.user, int(repository_id))
    return 204, None


@route("PATCH", r"/repositories/(\d+)")
def update_description(req, repository_id):
    return 200, service.update_description(req.store, req.user, int(repository_id), req.body)


@route("GET", r"/repositories/(\d+)/analysis")
def get_analysis(req, repository_id):
    return 200, service.get_analysis(req.store, req.user, int(repository_id))


@route("POST", r"/repositories/(\d+)/scan")
def scan_repository(req, repository_id):
    return 200, service.scan_repository(req.store, req.user, int(repository_id))


# --- Plumbing ------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    server_version = "RepoRegistry/1.0"

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        parts = urlsplit(self.path)
        path = parts.path.rstrip("/") or "/"
        query = {key: values[-1] for key, values in parse_qs(parts.query).items()}

        allowed = []
        for route_method, pattern, func in ROUTES:
            match = pattern.match(path)
            if not match:
                continue
            if route_method != method:
                allowed.append(route_method)
                continue

            try:
                body = self._read_json()
            except BodyError as error:
                self._send(error.status, {"error": str(error)})
                return
            except ValueError as error:
                self._send(400, {"error": f"Body is not valid JSON: {error}"})
                return

            request = Request(self.server.store, self.headers.get("X-User", DEFAULT_USER), query, body)
            try:
                status, payload = func(request, *match.groups())
            except service.ServiceError as error:
                status, payload = error.status, {"error": str(error)}
            except Exception as error:  # a bug: show it instead of hiding it
                traceback.print_exc()
                status, payload = 500, {"error": f"Internal error: {error}"}
            self._send(status, payload)
            return

        if allowed:
            # Built from ROUTES, so it is always all and only the methods this path supports.
            allow = ", ".join(sorted(set(allowed)))
            self._send(405, {"error": f"{method} is not allowed here. Allowed: {allow}"}, headers={"Allow": allow})
        else:
            self._send(404, {"error": f"No endpoint for {method} {path}"})

    def _read_json(self):
        # Check the length before reading anything: a negative length would make read()
        # wait for the client to close, blocking this single-threaded server for everyone.
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise BodyError(400, "Content-Length must be a whole number") from None
        if length < 0:
            raise BodyError(400, "Content-Length must not be negative")
        if length > MAX_BODY:
            raise BodyError(413, "Request body is too large")
        if not length:
            return None
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send(self, status, payload, headers=None):
        data = b"" if payload is None else json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        if not self.server.quiet:
            super().log_message(format, *args)


class RegistryServer(HTTPServer):
    def __init__(self, address, store=None, quiet=False):
        super().__init__(address, Handler)
        self.store = store or Store()
        self.quiet = quiet


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the repository registry API.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data", default="data/registry.json",
                        help="JSON file the data is saved in (default data/registry.json)")
    parser.add_argument("--reset", action="store_true",
                        help="Start from the seed data and overwrite the data file")
    args = parser.parse_args(argv)

    try:
        store = Store(args.data, reset=args.reset)
    except (DataFileError, OSError) as error:
        raise SystemExit(f"Can't start: {error}")

    server = RegistryServer(("127.0.0.1", args.port), store=store)
    print(f"Repository registry running on http://localhost:{args.port}, data in {args.data} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
