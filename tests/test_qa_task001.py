"""QA checks for TASK-001: register a repository (POST /repositories).

AC tests check requirements.md. The test_risk_* tests record what the code does
today on security-relevant input, as evidence for the SECURITY review in qa.md.
They pass because they describe current behaviour, not because it is approved.
"""

import unittest

from app import service
from app.store import Store


def body(name="qa-repo", url="https://example.com/qa/repo", **extra):
    return {"name": name, "url": url, **extra}


class QaTask001(unittest.TestCase):
    def setUp(self):
        self.store = Store()

    # --- Acceptance criteria -----------------------------------------------------

    def test_ac1_created_with_values_and_owned_by_caller(self):
        repo = service.register_repository(self.store, "chen", body(name="  tools  ", url=" http://git.local/t "))
        self.assertEqual((repo["name"], repo["url"], repo["owner"]), ("tools", "http://git.local/t", "chen"))

    def test_ac2_description_optional(self):
        with_desc = service.register_repository(self.store, "chen", body(url="https://a.example/1", description="hi"))
        without = service.register_repository(self.store, "chen", body(url="https://a.example/2"))
        self.assertEqual(service.get_repository(self.store, "chen", with_desc["id"])["description"], "hi")
        self.assertIsNone(without["description"])

    def test_ac3_wrong_input_rejected_and_nothing_created(self):
        before = dict(self.store.repositories)
        for bad in (body(name="   "), {"url": "https://x.example/r"}, body(url=None),
                    body(url="ftp://x.example/r"), body(url="example.com/r"), body(url="https://")):
            with self.subTest(bad=bad), self.assertRaises(service.Invalid):
                service.register_repository(self.store, "chen", bad)
        self.assertEqual(self.store.repositories, before)

    def test_ac4_owner_sees_it_and_another_user_cannot(self):
        repo = service.register_repository(self.store, "chen", body())
        self.assertIn(repo["id"], [r["id"] for r in service.list_repositories(self.store, "chen")])
        with self.assertRaises(service.Forbidden):
            service.get_repository(self.store, "alice", repo["id"])

    def test_ac5_analysis_available_at_once(self):
        repo = service.register_repository(self.store, "chen", body())
        self.assertEqual(service.get_analysis(self.store, "chen", repo["id"])["repository_id"], repo["id"])

    def test_ac6_duplicate_url_rejected_across_users(self):
        service.register_repository(self.store, "chen", body(url="https://dup.example/r"))
        count = len(self.store.repositories)
        with self.assertRaises(service.Conflict):
            service.register_repository(self.store, "bob", body(url="  https://dup.example/r "))
        self.assertEqual(len(self.store.repositories), count)

    def test_existing_seed_repositories_still_work(self):
        names = [r["name"] for r in service.list_repositories(self.store, "alice")]
        self.assertIn("payments-api", names)

    # --- Security evidence (current behaviour, for SECURITY to judge) -------------

    def test_risk_credentials_in_url_are_stored_and_returned(self):
        url = "https://qa-user:ghp_FAKE_TOKEN_123@github.com/org/private"
        repo = service.register_repository(self.store, "chen", body(url=url))
        self.assertIn("ghp_FAKE_TOKEN_123", repo["url"])
        self.assertIn("ghp_FAKE_TOKEN_123", service.get_repository(self.store, "chen", repo["id"])["url"])

    def test_risk_no_length_limit_on_fields(self):
        huge = "x" * 2_000_000
        repo = service.register_repository(self.store, "chen", body(name=huge, description=huge))
        self.assertEqual(len(self.store.repositories[repo["id"]]["name"]), 2_000_000)

    def test_risk_conflict_reveals_another_users_url(self):
        # Accepted by the Product Owner (duplicates across all users); recorded, not blocking.
        service.register_repository(self.store, "chen", body(url="https://secret.example/chen"))
        with self.assertRaises(service.Conflict):
            service.register_repository(self.store, "bob", body(url="https://secret.example/chen"))


if __name__ == "__main__":
    unittest.main()
