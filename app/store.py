"""Data for the sample app.

By default everything lives in memory and starts from the seed data below.
Give Store a path and it also keeps a JSON snapshot on disk, so changes survive
a restart. There is no database on purpose, so the workshop needs no installs.
"""

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path

from . import analyzer


class DataFileError(Exception):
    """The data file exists but can't be read. Never reseed quietly: that would bring removed data back."""

SEED_USERS = {
    "alice": {"username": "alice", "name": "Alice", "email": "alice@example.com"},
    "bob": {"username": "bob", "name": "Bob", "email": "bob@example.com"},
    "chen": {"username": "chen", "name": "Chen", "email": "chen@example.com"},
}

SEED_REPOSITORIES = [
    {
        "id": 1,
        "name": "payments-api",
        "url": "https://github.com/example-org/payments-api",
        "description": "Card payment service",
        "owner": "alice",
        "registered_at": "2026-10-01T09:00:00Z",
        "last_scanned_at": "2026-11-20T08:00:00Z",
    },
    {
        "id": 2,
        "name": "web-portal",
        "url": "https://gitlab.com/example-org/web-portal",
        "description": "Customer self-service website",
        "owner": "alice",
        "registered_at": "2026-10-03T14:30:00Z",
        "last_scanned_at": "2026-11-21T08:00:00Z",
    },
    {
        "id": 3,
        "name": "data-pipeline",
        "url": "https://github.com/example-org/data-pipeline",
        "description": "Nightly reporting jobs",
        "owner": "bob",
        "registered_at": "2026-10-10T11:15:00Z",
        "last_scanned_at": "2026-11-22T08:00:00Z",
    },
    {
        "id": 4,
        "name": "mobile-app",
        "url": "https://bitbucket.org/example-org/mobile-app",
        "description": "iOS and Android app",
        "owner": "chen",
        "registered_at": "2026-10-15T16:45:00Z",
        "last_scanned_at": "2026-11-23T08:00:00Z",
    },
]


class Store:
    """All app data. Call reset() to go back to the seed data.

    Store() keeps data in memory only. Store(path) loads the JSON file at path if
    it exists (otherwise starts from the seed data) and saves after every change.
    Store(path, reset=True) ignores the file and saves fresh seed data to it.
    """

    def __init__(self, path=None, reset=False):
        self.path = Path(path) if path else None
        if self.path and self.path.exists() and not reset:
            self.load()
        else:
            self.reset()

    def reset(self):
        self.users = deepcopy(SEED_USERS)
        repositories = {repo["id"]: deepcopy(repo) for repo in SEED_REPOSITORIES}
        analyses = {
            repo_id: analyzer.analyze(repo, repo["last_scanned_at"])
            for repo_id, repo in repositories.items()
        }
        self.commit(repositories, analyses, max(repositories) + 1)

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            users = data["users"]
            repositories = {int(key): value for key, value in data["repositories"].items()}
            analyses = {int(key): value for key, value in data["analyses"].items()}
            next_id = int(data["next_id"])
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise DataFileError(
                f"Can't read the data file {self.path}: {error}. "
                "Fix or delete it, or start with --reset to go back to the seed data."
            ) from error
        self.users, self.repositories, self.analyses, self.next_id = users, repositories, analyses, next_id

    def commit(self, repositories, analyses, next_id):
        """Save the new state first, then swap it in, so memory never runs ahead of the file.

        If saving fails, it raises OSError and both memory and the file stay as they were.
        """
        if self.path:
            self._save({
                "users": self.users,
                "repositories": repositories,
                "analyses": analyses,
                "next_id": next_id,
            })
        self.repositories, self.analyses, self.next_id = repositories, analyses, next_id

    def _save(self, data):
        """Write atomically: a temp file in the same folder, then os.replace."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_path = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as temp:
                json.dump(data, temp, indent=2)
            os.replace(temp_path, self.path)
        except BaseException:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
