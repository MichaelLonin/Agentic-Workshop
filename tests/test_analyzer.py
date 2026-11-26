"""The analysis summary wording (TASK-006)."""

import unittest

from app import analyzer, service
from app.store import Store


def repo_with(open_findings):
    """A repository whose URL hashes to exactly this many open findings."""
    for n in range(10_000):
        repo = {"id": 99, "url": f"https://example.com/r{n}"}
        if analyzer.analyze(repo, "2026-01-01T00:00:00Z")["open_findings"] == open_findings:
            return repo
    raise AssertionError(f"no URL found with {open_findings} open findings")


class FindingsWordingTests(unittest.TestCase):
    def test_findings_text(self):
        self.assertEqual(analyzer.findings_text(0), "0 open findings")
        self.assertEqual(analyzer.findings_text(1), "1 open finding")
        self.assertEqual(analyzer.findings_text(2), "2 open findings")
        self.assertEqual(analyzer.findings_text(11), "11 open findings")

    def test_summary_uses_the_right_wording(self):
        for count, ending in ((1, ". 1 open finding."), (0, ". 0 open findings."), (2, ". 2 open findings.")):
            with self.subTest(count=count):
                result = analyzer.analyze(repo_with(count), "2026-01-01T00:00:00Z")
                self.assertEqual(result["open_findings"], count)
                self.assertTrue(result["summary"].endswith(ending), result["summary"])

    def test_only_the_wording_changed(self):
        result = analyzer.analyze(repo_with(1), "2026-01-01T00:00:00Z")
        old_style = f"{result['files']} files, mostly {max(result['languages'], key=result['languages'].get)}. 1 open findings."
        self.assertEqual(result["summary"], old_style.replace("1 open findings.", "1 open finding."))

    def test_registration_and_rescan_use_the_new_wording(self):
        store = Store()
        url = repo_with(1)["url"]
        repo = service.register_repository(store, "bob", {"name": "one-finding", "url": url})
        self.assertTrue(service.get_analysis(store, "bob", repo["id"])["summary"].endswith("1 open finding."))
        self.assertTrue(service.scan_repository(store, "bob", repo["id"])["summary"].endswith("1 open finding."))


if __name__ == "__main__":
    unittest.main()
