# Implementation: TASK-001

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real implementation, not a stub. `POST /repositories` registers a repository for the caller and returns `201` and the full repository, in the same shape as `GET /repositories/{id}`. It follows `architecture.md`:

- It checks the user first (401), then the body (400), then duplicates (409), and only then stores anything.
- It stores the name and URL with surrounding whitespace trimmed. `description` is optional and stored as `null` when it's absent.
- A URL must be absolute `http` or `https` with a host (`urlsplit`). A URL that `urlsplit` can't parse is a 400.
- Duplicates: the trimmed URL must not equal the trimmed URL of any existing repository, from any owner. The comparison is exact and case-sensitive.
- The analysis is created in the same call, so `GET /repositories/{id}/analysis` works straight away. `registered_at` and `last_scanned_at` are the same timestamp.

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
