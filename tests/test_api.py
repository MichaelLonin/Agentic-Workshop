import json
import socket
from copy import deepcopy
import threading
import unittest
import urllib.error
import urllib.request

from app.server import MAX_BODY, RegistryServer

# Ignore any system proxy: these requests go to a server on this machine.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = RegistryServer(("127.0.0.1", 0), quiet=True)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.server.store.reset()

    def call(self, method, path, user=None, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if user:
            request.add_header("X-User", user)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with OPENER.open(request, timeout=5) as response:
                return response.status, json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"null")

    def test_health(self):
        self.assertEqual(self.call("GET", "/health"), (200, {"status": "ok"}))

    def test_list_defaults_to_alice(self):
        status, repos = self.call("GET", "/repositories")
        self.assertEqual(status, 200)
        self.assertEqual([repo["owner"] for repo in repos], ["alice", "alice"])

    def test_list_for_another_user(self):
        status, repos = self.call("GET", "/repositories", user="bob")
        self.assertEqual(status, 200)
        self.assertEqual([repo["name"] for repo in repos], ["data-pipeline"])

    def test_unknown_user(self):
        status, _ = self.call("GET", "/repositories", user="mallory")
        self.assertEqual(status, 401)

    def test_other_users_repository_is_forbidden(self):
        status, _ = self.call("GET", "/repositories/3", user="alice")
        self.assertEqual(status, 403)

    def test_missing_repository(self):
        status, _ = self.call("GET", "/repositories/999")
        self.assertEqual(status, 404)

    def test_analysis_and_scan(self):
        status, analysis = self.call("GET", "/repositories/1/analysis")
        self.assertEqual(status, 200)
        self.assertEqual(analysis["repository_id"], 1)

        status, rescanned = self.call("POST", "/repositories/1/scan")
        self.assertEqual(status, 200)
        self.assertNotEqual(rescanned["scanned_at"], analysis["scanned_at"])

    def test_unknown_endpoint(self):
        status, _ = self.call("GET", "/nope")
        self.assertEqual(status, 404)

    def test_wrong_method(self):
        status, _ = self.call("PUT", "/health")
        self.assertEqual(status, 405)

    def test_invalid_json_body(self):
        request = urllib.request.Request(
            self.base + "/repositories/1/scan", data=b"{not json", method="POST"
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            OPENER.open(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)

    # TASK-001: POST /repositories

    def test_register_repository(self):
        body = {"name": "new-service", "url": "https://github.com/example-org/new-service", "description": "Jobs"}
        status, repo = self.call("POST", "/repositories", user="bob", body=body)
        self.assertEqual(status, 201)
        self.assertEqual((repo["name"], repo["owner"], repo["description"]), ("new-service", "bob", "Jobs"))

        status, repos = self.call("GET", "/repositories", user="bob")
        self.assertIn(repo["id"], [r["id"] for r in repos])
        status, analysis = self.call("GET", f"/repositories/{repo['id']}/analysis", user="bob")
        self.assertEqual((status, analysis["repository_id"]), (200, repo["id"]))
        status, _ = self.call("GET", f"/repositories/{repo['id']}", user="alice")
        self.assertEqual(status, 403)

    def test_register_invalid_body_is_400_and_creates_nothing(self):
        status, body = self.call("POST", "/repositories", body={"name": "x", "url": "not a url"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)
        _, repos = self.call("GET", "/repositories")
        self.assertEqual(len(repos), 2)

    # TASK-002: DELETE /repositories/{id}

    def test_remove_repository(self):
        self.assertEqual(self.call("DELETE", "/repositories/1", user="alice"), (204, None))
        for method, path in (("GET", "/repositories/1"), ("GET", "/repositories/1/analysis"),
                             ("POST", "/repositories/1/scan"), ("DELETE", "/repositories/1")):
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path, user="alice")[0], 404)
        _, repos = self.call("GET", "/repositories", user="alice")
        self.assertEqual([repo["id"] for repo in repos], [2])

    # TASK-005: GET ignores the request body

    def get_with_body(self, path, data, user=None):
        request = urllib.request.Request(self.base + path, data=data, method="GET")
        if user:
            request.add_header("X-User", user)
        try:
            with OPENER.open(request, timeout=5) as response:
                return response.status, json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"null")

    def test_get_health_ignores_any_body(self):
        expected = self.call("GET", "/health")
        self.assertEqual(expected, (200, {"status": "ok"}))
        for data in (b'{"ping": 1}', b"{not json", b"hello monitor", b"\xff\xfe"):
            with self.subTest(data=data):
                self.assertEqual(self.get_with_body("/health", data), expected)

    def test_other_gets_answer_the_same_with_a_body(self):
        before = deepcopy(self.server.store.repositories)
        for path, user in (("/repositories", "alice"), ("/repositories/1", "alice"),
                           ("/repositories/1/analysis", "alice"), ("/repositories/999", "alice"),
                           ("/repositories/3", "alice"), ("/repositories", "mallory")):
            with self.subTest(path=path, user=user):
                self.assertEqual(self.get_with_body(path, b'{"description": "hacked"}', user=user),
                                 self.call("GET", path, user=user))
        self.assertEqual(self.server.store.repositories, before)

    def test_non_get_still_rejects_bad_json(self):
        request = urllib.request.Request(self.base + "/repositories", data=b"{not json", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            OPENER.open(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)
        self.assertIn("not valid JSON", json.loads(caught.exception.read())["error"])

    # TASK-004: Allow header on 405

    def raw(self, method, path):
        """(status, Allow header as a set of methods or None, JSON body) for one request."""
        request = urllib.request.Request(self.base + path, method=method)
        try:
            with OPENER.open(request, timeout=5) as response:
                status, headers, data = response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            status, headers, data = error.code, error.headers, error.read()
        allow = headers.get("Allow")
        methods = {part.strip() for part in allow.split(",")} if allow is not None else None
        return status, methods, json.loads(data or b"null")

    def test_405_lists_the_allowed_methods(self):
        # PATCH on /repositories/{id} comes from TASK-003, so it is supported and listed (AC1).
        expected = {
            ("PUT", "/health"): {"GET"},
            ("PUT", "/repositories"): {"GET", "POST"},
            ("POST", "/repositories/1"): {"DELETE", "GET", "PATCH"},
            ("PUT", "/repositories/1/analysis"): {"GET"},
            ("PUT", "/repositories/1/scan"): {"POST"},
        }
        for (method, path), methods in expected.items():
            with self.subTest(method=method, path=path):
                status, allow, body = self.raw(method, path)
                self.assertEqual((status, allow), (405, methods))
                self.assertEqual(body, {"error": f"{method} is not allowed here. Allowed: {', '.join(sorted(methods))}"})

    def test_405_ignores_query_string_and_trailing_slash(self):
        for path in ("/repositories?page=2", "/repositories/", "/repositories/?page=2"):
            with self.subTest(path=path):
                self.assertEqual(self.raw("PUT", path)[:2], (405, {"GET", "POST"}))

    def test_no_allow_header_on_404_or_success(self):
        self.assertEqual(self.raw("PUT", "/nope")[:2], (404, None))
        self.assertEqual(self.raw("GET", "/health")[:2], (200, None))

    # TASK-003: PATCH /repositories/{id}

    def test_update_description(self):
        _, analysis_before = self.call("GET", "/repositories/1/analysis", user="alice")
        status, repo = self.call("PATCH", "/repositories/1", user="alice", body={"description": "Payments v2"})
        self.assertEqual((status, repo["description"], repo["name"]), (200, "Payments v2", "payments-api"))
        self.assertEqual(self.call("GET", "/repositories/1", user="alice")[1]["description"], "Payments v2")
        self.assertEqual(self.call("GET", "/repositories/1/analysis", user="alice")[1], analysis_before)

    def test_update_description_errors(self):
        self.assertEqual(self.call("PATCH", "/repositories/1", user="bob", body={"description": "x"})[0], 403)
        self.assertEqual(self.call("PATCH", "/repositories/1", user="mallory", body={"description": "x"})[0], 401)
        self.assertEqual(self.call("PATCH", "/repositories/999", user="alice", body={"description": "x"})[0], 404)
        self.assertEqual(self.call("PATCH", "/repositories/1", user="alice", body={"name": "x"})[0], 400)
        self.assertEqual(self.call("PATCH", "/repositories/1", user="alice")[0], 400)
        self.assertEqual(self.call("GET", "/repositories/1", user="alice")[1]["description"], "Card payment service")

    def test_remove_is_denied_for_others_and_unknown_users(self):
        self.assertEqual(self.call("DELETE", "/repositories/1", user="bob")[0], 403)
        self.assertEqual(self.call("DELETE", "/repositories/1", user="mallory")[0], 401)
        self.assertEqual(self.call("GET", "/repositories/1", user="alice")[0], 200)

    # TASK-001 security review: credentials in URLs and request size limits

    def test_register_url_with_credentials_is_400_without_echo(self):
        body = {"name": "private", "url": "https://user:SECRET_TOKEN@github.com/org/private"}
        status, error = self.call("POST", "/repositories", user="bob", body=body)
        self.assertEqual(status, 400)
        self.assertNotIn("SECRET_TOKEN", json.dumps(error))
        self.assertEqual(len(self.call("GET", "/repositories", user="bob")[1]), 1)

    def send_headers_only(self, content_length):
        """POST with this Content-Length and no body. Answering at all proves the body was not read."""
        host, port = self.server.server_address
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall((f"POST /repositories HTTP/1.0\r\nX-User: bob\r\n"
                          f"Content-Length: {content_length}\r\n\r\n").encode("ascii"))
            response = b""
            while chunk := sock.recv(65536):
                response += chunk
        head, _, body = response.partition(b"\r\n\r\n")
        return int(head.split(b" ", 2)[1]), json.loads(body)

    def test_oversized_negative_or_bad_content_length_is_refused_unread(self):
        self.assertEqual(self.send_headers_only(MAX_BODY + 1), (413, {"error": "Request body is too large"}))
        self.assertEqual(self.send_headers_only(-1)[0], 400)
        self.assertEqual(self.send_headers_only("abc")[0], 400)
        self.assertEqual(len(self.call("GET", "/repositories", user="bob")[1]), 1)

    def test_body_just_under_the_limit_is_still_read(self):
        body = {"name": "padded", "url": "https://example.com/padded", "padding": "x" * 60000}
        status, repo = self.call("POST", "/repositories", user="bob", body=body)
        self.assertEqual((status, repo["name"]), (201, "padded"))

    def test_register_duplicate_url_is_409(self):
        body = {"name": "copy", "url": "https://github.com/example-org/data-pipeline"}
        status, _ = self.call("POST", "/repositories", user="alice", body=body)
        self.assertEqual(status, 409)


if __name__ == "__main__":
    unittest.main()
