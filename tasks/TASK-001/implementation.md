# Implementation: TASK-001

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real implementation, not a stub. `POST /repositories` registers a repository for the caller and returns `201` and the full repository, in the same shape as `GET /repositories/{id}`. It follows `architecture.md`:

- It checks the user first (401), then the body (400), then duplicates (409), and only then stores anything.
- It stores the name and URL with surrounding whitespace trimmed. `description` is optional and stored as `null` when it's absent.
- A URL must be absolute `http` or `https` with a host (`urlsplit`). A URL that `urlsplit` can't parse is a 400.
- Duplicates: the trimmed URL must not equal the trimmed URL of any existing repository, from any owner. The comparison is exact and case-sensitive.
- The analysis is created in the same call, so `GET /repositories/{id}/analysis` works straight away. `registered_at` and `last_scanned_at` are the same timestamp.

**Attempt 2: the SECURITY review's changes (`architecture.md`, "SECURITY review, attempt 1"):**

- **Credentials in URLs are rejected:** a URL with any user-info part (`user@`, `user:pw@`, `:pw@` or an empty `@`) gets `400` with `'url' must not contain a username or password`. The URL is never echoed, and nothing is stored.
- **Field limits** (`app/service.py`, constants `MAX_NAME = 200`, `MAX_URL = 2048`, `MAX_DESCRIPTION = 2000`): name and URL are checked after trimming. The description is checked as stored, because it isn't trimmed. Anything longer gets `400`. As the review asked, `update_description` (TASK-003) uses the same `MAX_DESCRIPTION`.
- **Request body limits** (`app/server.py`, `_read_json`, for every endpoint): `Content-Length` is checked before anything is read. Not a number or negative gets `400`; over `MAX_BODY = 64 KiB` gets `413` `{"error": "Request body is too large"}`, unread.

## Files changed

- `app/service.py`: new `Conflict` error (409), `_is_web_url()` and `register_repository()`.
- `app/server.py`: route `POST /repositories`, which returns 201.
- `docs/api.md`: a row for the new endpoint.
- `tests/test_service.py`: 6 tests covering AC1–AC6 and the 401 case. The bad-input test covers 11 different bodies.
- `tests/test_api.py`: 3 HTTP tests (201 with list, analysis and 403 for another user; 400; 409).

## Tests

`python3 -m unittest` → `Ran 33 tests ... OK` (24 before, plus 9 new).

## Known limits

- These are deliberate, as `architecture.md` says: URLs are compared as exact text, so `https://x.com/a` and `https://x.com/a/` count as different; nothing has a length limit; data is in memory and is lost when the app restarts.
- `description` isn't trimmed or checked beyond "string or null", so an empty string is accepted.
- `POST /repositories` with no body returns 400 ("Send a JSON object…"), not 411.

## Attempts

- Attempt 1: first version.
- Attempt 2: the SECURITY review's fixes (credentials in URLs rejected, field limits, request body limits). The limits also apply to TASK-003's description update and to every endpoint's request body. A 2,001-character description is now rejected by `PATCH` too, so QA should know this when checking TASK-003. Clients still uploading a body over 64 KiB may see the connection close before they read the `413`, because the server answers without reading the body, as designed.
