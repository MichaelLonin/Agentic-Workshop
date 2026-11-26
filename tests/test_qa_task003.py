"""QA checks for TASK-003: change a repository's description (PATCH /repositories/{id})."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path
from unittest import mock

from app import service
from app.server import RegistryServer
from app.store import Store

NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def snapshot(store):
    return deepcopy((store.repositories, store.analyses, store.next_id))


class QaTask003(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "registry.json"

    def tearDown(self):
        self.temp.cleanup()

    def update(self, body, user="alice", repo_id=1, store=None):
        return service.update_description(store or self.store, user, repo_id, body)

    # --- Acceptance criteria -----------------------------------------------------

    def test_ac1_owner_updates_and_next_read_shows_it(self):
        result = self.update({"description": "Card and wallet payments"})
        self.assertEqual(result["description"], "Card and wallet payments")
        self.assertEqual(service.get_repository(self.store, "alice", 1)["description"], "Card and wallet payments")

    def test_ac2_empty_string_and_null_are_allowed(self):
        self.assertEqual(self.update({"description": ""})["description"], "")
        self.assertIsNone(self.update({"description": None})["description"])
        self.assertIsNone(service.get_repository(self.store, "alice", 1)["description"])

    def test_ac2_bad_bodies_rejected_and_nothing_changes(self):
        before = snapshot(self.store)
        for bad in (None, [], "text", {}, {"description": 5}, {"description": ["a"]},
                    {"description": "ok", "name": "renamed"}, {"description": "ok", "owner": "bob"}):
            with self.subTest(bad=bad), self.assertRaises(service.Invalid):
                self.update(bad)
        self.assertEqual(snapshot(self.store), before)

    def test_ac3_unknown_user_non_owner_and_missing_repository(self):
        before = snapshot(self.store)
        with self.assertRaises(service.Unauthorized):
            self.update({"description": "x"}, user="mallory")
        with self.assertRaises(service.Forbidden):
            self.update({"description": "x"}, user="bob")
        with self.assertRaises(service.Forbidden):  # access is checked before the body
            self.update({"description": 5}, user="bob")
        with self.assertRaises(service.NotFound):
            self.update({"description": "x"}, repo_id=999)
        self.assertEqual(snapshot(self.store), before)

    def test_ac4_only_the_description_changes(self):
        repos, analyses, next_id = snapshot(self.store)
        self.update({"description": "new text"})
        expected = deepcopy(repos)
        expected[1]["description"] = "new text"
        self.assertEqual(self.store.repositories, expected)  # every other field and repository identical
        self.assertEqual(self.store.analyses, analyses)       # analysis not re-run or changed
        self.assertEqual(self.store.next_id, next_id)

    def test_ac5_file_backed_change_survives_restart(self):
        self.update({"description": "saved"}, store=Store(self.path))
        self.assertEqual(Store(self.path).repositories[1]["description"], "saved")

    def test_ac5_failed_save_reports_error_and_changes_nothing(self):
        store = Store(self.path)
        before, file_before = snapshot(store), self.path.read_text(encoding="utf-8")
        with mock.patch("app.store.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(service.StorageError):
                self.update({"description": "lost"}, store=store)
        self.assertEqual(snapshot(store), before)
        self.assertEqual(self.path.read_text(encoding="utf-8"), file_before)

    # --- Other checks ------------------------------------------------------------

    def test_description_limit_also_applies_to_update(self):
        before = snapshot(self.store)
        with self.assertRaises(service.Invalid):
            self.update({"description": "x" * (service.MAX_DESCRIPTION + 1)})
        self.assertEqual(snapshot(self.store), before)
        self.assertEqual(len(self.update({"description": "x" * service.MAX_DESCRIPTION})["description"]),
                         service.MAX_DESCRIPTION)

    def test_works_on_a_newly_registered_repository(self):
        repo = service.register_repository(self.store, "chen", {"name": "n", "url": "https://qa.example/t3"})
        self.assertEqual(self.update({"description": "d"}, user="chen", repo_id=repo["id"])["description"], "d")

    def test_worked_before_detail_unchanged_without_update(self):
        self.assertEqual(service.get_repository(self.store, "alice", 1)["description"], "Card payment service")


class QaTask003Api(unittest.TestCase):
    def setUp(self):
        self.server = RegistryServer(("127.0.0.1", 0), quiet=True)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, user=None, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if user:
            request.add_header("X-User", user)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with NO_PROXY.open(request, timeout=5) as response:
                return response.status, json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"null")

    def test_http_patch_returns_200_with_full_repository(self):
        status, body = self.call("PATCH", "/repositories/1", "alice", {"description": "via http"})
        self.assertEqual(status, 200)
        self.assertEqual(body, self.call("GET", "/repositories/1", "alice")[1])
        self.assertEqual(body["description"], "via http")

    def test_http_error_codes(self):
        self.assertEqual(self.call("PATCH", "/repositories/1", "mallory", {"description": "x"})[0], 401)
        self.assertEqual(self.call("PATCH", "/repositories/1", "bob", {"description": "x"})[0], 403)
        self.assertEqual(self.call("PATCH", "/repositories/999", "alice", {"description": "x"})[0], 404)
        self.assertEqual(self.call("PATCH", "/repositories/1", "alice", {"name": "x"})[0], 400)
        self.assertEqual(self.call("GET", "/repositories/1", "alice")[1]["description"], "Card payment service")


if __name__ == "__main__":
    unittest.main()
