import unittest

from app import analyzer, service
from app.store import Store


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()

    def test_list_shows_only_my_repositories(self):
        names = [repo["name"] for repo in service.list_repositories(self.store, "alice")]
        self.assertEqual(names, ["payments-api", "web-portal"])

    def test_unknown_user_is_rejected(self):
        with self.assertRaises(service.Unauthorized):
            service.list_repositories(self.store, "mallory")

    def test_cannot_open_someone_elses_repository(self):
        with self.assertRaises(service.Forbidden):
            service.get_repository(self.store, "bob", 1)

    def test_missing_repository(self):
        with self.assertRaises(service.NotFound):
            service.get_repository(self.store, "alice", 999)

    def test_scan_updates_time_and_analysis(self):
        before = service.get_repository(self.store, "alice", 1)["last_scanned_at"]
        analysis = service.scan_repository(self.store, "alice", 1)
        after = service.get_repository(self.store, "alice", 1)["last_scanned_at"]
        self.assertNotEqual(before, after)
        self.assertEqual(analysis["scanned_at"], after)

    def test_analysis_is_stable_for_the_same_url(self):
        repo = self.store.repositories[1]
        first = analyzer.analyze(repo, "2026-01-01T00:00:00Z")
        second = analyzer.analyze(repo, "2026-01-01T00:00:00Z")
        self.assertEqual(first, second)
        self.assertEqual(sum(first["languages"].values()), 100)

    # TASK-001: registering a repository

    def register(self, user="bob", **body):
        body.setdefault("name", "new-service")
        body.setdefault("url", "https://github.com/example-org/new-service")
        return service.register_repository(self.store, user, body)

    def test_register_creates_a_repository_owned_by_the_caller(self):
        repo = self.register(name="  new-service ", url=" https://github.com/example-org/new-service ")
        self.assertEqual(repo["id"], 5)
        self.assertEqual(repo["name"], "new-service")
        self.assertEqual(repo["url"], "https://github.com/example-org/new-service")
        self.assertEqual(repo["owner"], "bob")
        self.assertEqual(repo["registered_at"], repo["last_scanned_at"])
        names = [r["name"] for r in service.list_repositories(self.store, "bob")]
        self.assertEqual(names, ["data-pipeline", "new-service"])

    def test_register_keeps_the_description_and_works_without_one(self):
        with_text = self.register(description="Billing jobs")
        self.assertEqual(service.get_repository(self.store, "bob", with_text["id"])["description"], "Billing jobs")
        without = self.register(url="http://git.internal.example/team/tool")
        self.assertIsNone(service.get_repository(self.store, "bob", without["id"])["description"])

    def test_register_rejects_bad_input_and_creates_nothing(self):
        bad_bodies = [
            None,
            ["not", "an", "object"],
            {"url": "https://example.com/a"},
            {"name": "   ", "url": "https://example.com/a"},
            {"name": 7, "url": "https://example.com/a"},
            {"name": "a"},
            {"name": "a", "url": "example.com/a"},
            {"name": "a", "url": "ftp://example.com/a"},
            {"name": "a", "url": "https://"},
            {"name": "a", "url": "http://[::1"},
            {"name": "a", "url": "https://example.com/a", "description": 5},
        ]
        for body in bad_bodies:
            with self.subTest(body=body):
                with self.assertRaises(service.Invalid):
                    service.register_repository(self.store, "bob", body)
        self.assertEqual(len(self.store.repositories), 4)
        self.assertEqual(self.store.next_id, 5)

    def test_register_rejects_a_url_already_registered_by_anyone(self):
        with self.assertRaises(service.Conflict):
            self.register(user="chen", url="  https://github.com/example-org/payments-api  ")
        self.assertEqual(len(self.store.repositories), 4)

    def test_register_needs_a_known_user(self):
        with self.assertRaises(service.Unauthorized):
            self.register(user="mallory")

    def test_registered_repository_is_private_and_analysed_at_once(self):
        repo = self.register()
        analysis = service.get_analysis(self.store, "bob", repo["id"])
        self.assertEqual(analysis["repository_id"], repo["id"])
        self.assertEqual(analysis["scanned_at"], repo["last_scanned_at"])
        with self.assertRaises(service.Forbidden):
            service.get_repository(self.store, "alice", repo["id"])


if __name__ == "__main__":
    unittest.main()
