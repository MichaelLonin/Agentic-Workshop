"""Business logic for the repository registry.

Every function takes the store and the current user's username. The HTTP layer
in server.py only turns requests into calls to these functions, so new
features usually start here.
"""

from datetime import datetime, timezone
from urllib.parse import urlsplit

from . import analyzer


class ServiceError(Exception):
    """Base class for errors the API returns to the caller."""

    status = 400


class Invalid(ServiceError):
    status = 400


class Unauthorized(ServiceError):
    status = 401


class Forbidden(ServiceError):
    status = 403


class NotFound(ServiceError):
    status = 404


class Conflict(ServiceError):
    status = 409


class StorageError(ServiceError):
    status = 500


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_user(store, username):
    user = store.users.get(username)
    if user is None:
        raise Unauthorized(f"Unknown user: {username}")
    return user


def _summary(repo):
    return {"id": repo["id"], "name": repo["name"], "url": repo["url"], "owner": repo["owner"]}


def _get_owned(store, username, repository_id):
    require_user(store, username)
    repo = store.repositories.get(repository_id)
    if repo is None:
        raise NotFound(f"Repository {repository_id} not found")
    if repo["owner"] != username:
        raise Forbidden("You don't have access to this repository")
    return repo


def _commit(store, repositories, analyses, next_id):
    """Save the new state, then use it. If saving fails, nothing has changed."""
    try:
        store.commit(repositories, analyses, next_id)
    except OSError as error:
        raise StorageError(f"The change couldn't be saved, so nothing was changed: {error}") from error


def list_repositories(store, username):
    """The repositories the user owns, oldest first."""
    require_user(store, username)
    return [
        _summary(repo)
        for repo in sorted(store.repositories.values(), key=lambda r: r["id"])
        if repo["owner"] == username
    ]


def _is_web_url(url):
    """True for an absolute http or https URL with a host."""
    try:
        parts = urlsplit(url)
        return parts.scheme in ("http", "https") and bool(parts.hostname)
    except ValueError:
        return False


def register_repository(store, username, body):
    """Register a new repository for the caller and analyse it straight away.

    Everything is checked before anything is stored, so a rejected request creates nothing.
    """
    require_user(store, username)
    if not isinstance(body, dict):
        raise Invalid("Send a JSON object with 'name' and 'url'")

    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise Invalid("'name' is required and must not be blank")
    url = body.get("url")
    if not isinstance(url, str) or not _is_web_url(url.strip()):
        raise Invalid("'url' is required and must be an absolute http or https URL with a host")
    description = body.get("description")
    if description is not None and not isinstance(description, str):
        raise Invalid("'description' must be a string or null")

    name, url = name.strip(), url.strip()
    if any(repo["url"].strip() == url for repo in store.repositories.values()):
        raise Conflict("This URL is already registered")

    now = now_utc()
    repo = {
        "id": store.next_id,
        "name": name,
        "url": url,
        "description": description,
        "owner": username,
        "registered_at": now,
        "last_scanned_at": now,
    }
    repositories = {**store.repositories, repo["id"]: repo}
    analyses = {**store.analyses, repo["id"]: analyzer.analyze(repo, now)}
    _commit(store, repositories, analyses, store.next_id + 1)
    return dict(repo)


def get_repository(store, username, repository_id):
    return dict(_get_owned(store, username, repository_id))


def get_analysis(store, username, repository_id):
    _get_owned(store, username, repository_id)
    return dict(store.analyses[repository_id])


def scan_repository(store, username, repository_id):
    """Run the (pretend) analysis again now and return the new result."""
    repo = _get_owned(store, username, repository_id)
    scanned_at = now_utc()
    updated = {**repo, "last_scanned_at": scanned_at}
    repositories = {**store.repositories, repository_id: updated}
    analyses = {**store.analyses, repository_id: analyzer.analyze(updated, scanned_at)}
    _commit(store, repositories, analyses, store.next_id)
    return dict(analyses[repository_id])


def remove_repository(store, username, repository_id):
    """Remove one of the caller's repositories and its analysis, and nothing else.

    The id is never reused (next_id stays as it is), so it stays not found for good.
    """
    _get_owned(store, username, repository_id)
    repositories = {key: repo for key, repo in store.repositories.items() if key != repository_id}
    analyses = {key: analysis for key, analysis in store.analyses.items() if key != repository_id}
    _commit(store, repositories, analyses, store.next_id)
