# Architecture: TASK-001

<!-- Owner: ARCHITECT. Security notes: SECURITY. A few bullets, not a design document. -->

## Approach

- Add one endpoint, `POST /repositories`, following the existing pattern: the logic goes in a new `service.register_repository(store, username, body)`, plus a thin `@route` handler in `server.py`.
- Check the caller first with `require_user` (401). Then validate the body, then check for duplicates, and only then write to the store. That way a rejected request never creates anything (AC3, AC6).
- Owner = the caller (`req.user`). The id comes from `store.next_id`, which is then incremented. Set `registered_at` and `last_scanned_at` to the same `now_utc()` value.
- In the same call, run `analyzer.analyze(repo, scanned_at)` and store it in `store.analyses[id]`. `GET /repositories/{id}/analysis` then works straight away, with no scan (AC5).
- Ownership and visibility need no changes. The existing `list_repositories` and `_get_owned` already give the owner access and return 403 to anyone else (AC4).

## Parts that change

- `app/service.py`: add a `Conflict(ServiceError)` class with `status = 409`, and add `register_repository`.
- `app/server.py`: add `@route("POST", "/repositories")`. It returns `201` and the result of `register_repository`.
- `docs/api.md`: add a row for the new endpoint.
- `tests/test_service.py`, `tests/test_api.py`: add tests for AC1–AC6.
- Not changed: `app/store.py`, `app/analyzer.py` (out of scope per requirements).

## Interface

- **Request:** `POST /repositories`, header `X-User: <username>`, JSON body:
  - `name`: string, required. Trim it; it must not be empty after trimming. Store the trimmed value.
  - `url`: string, required. Trim surrounding whitespace and store the trimmed value. After trimming, `urllib.parse.urlsplit(url)` must give a scheme of `http` or `https` and a non-empty `hostname`. If `urlsplit` raises `ValueError`, the URL is invalid.
  - `description`: optional. A string, or absent/`null`. If it's absent, store `null`.
- **Success:** `201` with the full repository, in the same shape as `GET /repositories/{id}`: `id`, `name`, `url`, `description`, `owner`, `registered_at`, `last_scanned_at`.
- **Errors** (all `{"error": "<message>"}`, nothing stored):
  - `400`: the body is missing or isn't a JSON object; `name` is missing, not a string or blank; `url` is missing, not a string or not an absolute http/https URL with a host; `description` is not a string or null.
  - `401`: unknown user.
  - `409`: the trimmed `url` exactly equals the trimmed `url` of any existing repository, from any owner (case-sensitive, no other normalising).

## Risks and limits

- The duplicate check is plain text after trimming, as the PO decided, so `https://x.com/a` and `https://x.com/a/` count as different repositories. That's intentional, not a bug.
- A `409` tells the caller that someone else has already registered that URL, but it doesn't say who or which id. This follows from the PO's "duplicate across all users" decision.
- Everything stays in memory, so registered repositories disappear when the app restarts (existing behaviour, out of scope).
- There are no length limits on name, URL or description, because the requirements don't ask for any.
- The server is single-threaded (`HTTPServer`), so the duplicate check and the insert can't race.

## Security notes

- None reported. One design point: the analyser only hashes the URL and never fetches it, so there's no server-side request risk. Allowing only `http`/`https` also keeps out `file:`, `javascript:` and similar schemes.
