"""QA checks for TASK-002: remove a repository (DELETE /repositories/{id})."""

import json
import os
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
from app.store import DataFileError, Store

NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def snapshot(store):
    return deepcopy((store.repositories, store.analyses, store.next_id))


class QaTask002(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "registry.json"

    def tearDown(self):
        self.temp.cleanup()

    # --- Acceptance criteria -----------------------------------------------------

    def test_ac1_owner_removes_and_it_leaves_their_list(self):
        service.remove_repository(self.store, "alice", 1)
        self.assertNotIn(1, [r["id"] for r in service.list_repositories(self.store, "alice")])

    def test_ac2_gone_everywhere_including_analysis(self):
        service.remove_repository(self.store, "alice", 1)
        for call in (service.get_repository, service.get_analysis, service.scan_repository):
            with self.subTest(call=call.__name__), self.assertRaises(service.NotFound):
                call(self.store, "alice", 1)
        self.assertNotIn(1, self.store.analyses)

    def test_ac3_removal_survives_restart_and_reset_restores_seed(self):
        service.remove_repository(Store(self.path), "alice", 1)
        restarted = Store(self.path)
        self.assertNotIn(1, restarted.repositories)
        self.assertNotIn(1, restarted.analyses)
        self.assertIn(1, Store(self.path, reset=True).repositories)

    def test_ac4_other_users_repository_is_denied_and_unchanged(self):
        before = snapshot(self.store)
        with self.assertRaises(service.Forbidden):
            service.remove_repository(self.store, "bob", 1)
        self.assertEqual(snapshot(self.store), before)

    def test_ac5_unknown_user_and_absent_repository(self):
        before = snapshot(self.store)
        with self.assertRaises(service.Unauthorized):
            service.remove_repository(self.store, "mallory", 1)
        with self.assertRaises(service.NotFound):
            service.remove_repository(self.store, "alice", 999)
        self.assertEqual(snapshot(self.store), before)

    def test_ac6_failed_save_reports_failure_and_changes_nothing(self):
        store = Store(self.path)
        before, file_before = snapshot(store), self.path.read_text(encoding="utf-8")
        with mock.patch("app.store.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(service.StorageError):
                service.remove_repository(store, "alice", 1)
        self.assertEqual(snapshot(store), before)
        self.assertEqual(self.path.read_text(encoding="utf-8"), file_before)
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["registry.json"])  # no temp file left

    def test_ac6_other_repositories_and_analyses_unchanged(self):
        others = {k: v for k, v in snapshot(self.store)[0].items() if k != 1}
        other_analyses = {k: v for k, v in snapshot(self.store)[1].items() if k != 1}
        service.remove_repository(self.store, "alice", 1)
        self.assertEqual(self.store.repositories, others)
        self.assertEqual(self.store.analyses, other_analyses)

    # --- Other checks ------------------------------------------------------------

    def test_removing_twice_is_not_found(self):
        service.remove_repository(self.store, "alice", 1)
        with self.assertRaises(service.NotFound):
            service.remove_repository(self.store, "alice", 1)

    def test_removed_id_is_never_reused_even_after_restart(self):
        store = Store(self.path)
        new = service.register_repository(store, "chen", {"name": "n", "url": "https://qa.example/n"})
        service.remove_repository(store, "chen", new["id"])
        again = service.register_repository(Store(self.path), "chen", {"name": "n", "url": "https://qa.example/n"})
        self.assertGreater(again["id"], new["id"])

    def test_corrupt_data_file_stops_instead_of_reseeding(self):
        self.path.write_text("not json", encoding="utf-8")
        with self.assertRaises(DataFileError):
            Store(self.path)

    def test_worked_before_listing_still_works(self):
        names = [r["name"] for r in service.list_repositories(self.store, "alice")]
        self.assertEqual(names, ["payments-api", "web-portal"])


class QaTask002Api(unittest.TestCase):
    def setUp(self):
        self.server = RegistryServer(("127.0.0.1", 0), quiet=True)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, user=None):
        request = urllib.request.Request(self.base + path, method=method)
        if user:
            request.add_header("X-User", user)
        try:
            with NO_PROXY.open(request, timeout=5) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def test_http_delete_is_204_empty_then_404(self):
        self.assertEqual(self.call("DELETE", "/repositories/1", "alice"), (204, b""))
        for method, path in (("GET", "/repositories/1"), ("GET", "/repositories/1/analysis"),
                             ("POST", "/repositories/1/scan"), ("DELETE", "/repositories/1")):
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path, "alice")[0], 404)

    def test_http_wrong_user_and_unknown_user(self):
        self.assertEqual(self.call("DELETE", "/repositories/1", "bob")[0], 403)
        self.assertEqual(self.call("DELETE", "/repositories/1", "mallory")[0], 401)
        self.assertEqual(self.call("GET", "/repositories/1", "alice")[0], 200)


if __name__ == "__main__":
    unittest.main()
