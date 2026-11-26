"""Saving data to a file, so changes survive a restart (TASK-002, AC3 and AC6)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import service
from app.store import DataFileError, Store


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "data" / "registry.json"

    def test_without_a_path_nothing_is_written(self):
        store = Store()
        service.remove_repository(store, "alice", 1)
        self.assertFalse(self.path.parent.exists())

    def test_removal_survives_a_restart(self):
        service.remove_repository(Store(self.path), "alice", 1)
        restarted = Store(self.path)
        self.assertNotIn(1, restarted.repositories)
        self.assertNotIn(1, restarted.analyses)
        with self.assertRaises(service.NotFound):
            service.get_analysis(restarted, "alice", 1)
        self.assertEqual([r["name"] for r in service.list_repositories(restarted, "alice")], ["web-portal"])

    def test_registration_and_scan_survive_a_restart(self):
        store = Store(self.path)
        new = service.register_repository(store, "bob", {"name": "x", "url": "https://example.com/x"})
        scan = service.scan_repository(store, "alice", 2)
        restarted = Store(self.path)
        self.assertEqual(service.get_repository(restarted, "bob", new["id"])["url"], "https://example.com/x")
        self.assertEqual(service.get_analysis(restarted, "alice", 2), scan)
        self.assertEqual(restarted.next_id, 6)

    def test_reset_brings_back_the_seed_data(self):
        service.remove_repository(Store(self.path), "alice", 1)
        Store(self.path, reset=True)
        self.assertIn(1, Store(self.path).repositories)

    def test_a_failed_save_changes_nothing(self):
        store = Store(self.path)
        saved = self.path.read_text(encoding="utf-8")
        with mock.patch("app.store.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(service.StorageError) as caught:
                service.remove_repository(store, "alice", 1)
        self.assertEqual(caught.exception.status, 500)
        self.assertIn(1, store.repositories)
        self.assertIn(1, store.analyses)
        self.assertEqual(self.path.read_text(encoding="utf-8"), saved)
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["registry.json"])

    def test_a_description_change_survives_a_restart(self):
        service.update_description(Store(self.path), "bob", 3, {"description": "Hourly jobs"})
        self.assertEqual(service.get_repository(Store(self.path), "bob", 3)["description"], "Hourly jobs")

    def test_a_failed_description_save_changes_nothing(self):
        store = Store(self.path)
        saved = self.path.read_text(encoding="utf-8")
        with mock.patch("app.store.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(service.StorageError):
                service.update_description(store, "bob", 3, {"description": "Hourly jobs"})
        self.assertEqual(store.repositories[3]["description"], "Nightly reporting jobs")
        self.assertEqual(self.path.read_text(encoding="utf-8"), saved)

    def test_an_unreadable_file_stops_instead_of_reseeding(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("not json", encoding="utf-8")
        with self.assertRaises(DataFileError):
            Store(self.path)


if __name__ == "__main__":
    unittest.main()
