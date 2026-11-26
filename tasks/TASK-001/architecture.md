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

- Design point (unchanged): the analyser only hashes the URL and never fetches it, so there's no server-side request risk. Allowing only `http`/`https` keeps out `file:`, `javascript:` and similar schemes.

### SECURITY review, attempt 1 (QA finding `SECURITY_RISK`, qa.md)

Confirmed by reading `app/service.py` (`_is_web_url`, `register_repository`) and `app/server.py` (`_read_json`). The code must change, so the task goes back to DEVELOPER.

1. **Credentials in the URL: real risk, MUST FIX.** `https://user:TOKEN@host/...` passes `_is_web_url`. It is stored, returned by `POST` and `GET /repositories/{id}`, and, through the TASK-002 snapshot, written to `data/registry.json` in plain text. A registry has no reason to hold secrets.
   - **Change:** in `register_repository`, reject a URL whose `urlsplit` result has a `username` or `password` (i.e. an `@` user-info part). Return `400` `{"error": "'url' must not contain a username or password"}`. Reject it rather than quietly removing the part, so that what's stored is exactly what the user sent and the AC6 duplicate rule stays simple. Don't echo the URL back in the error message.
   - **Note for the PO:** this narrows AC1 by one case (URLs with credentials are no longer "valid"). It doesn't touch the PO's decision to accept any host.
2. **No size limits: real risk, MUST FIX (scaled to the workshop).** `_read_json` reads whatever `Content-Length` says, and the data is kept for good, so one request can make memory and the data file grow without limit. A **negative** `Content-Length` makes `rfile.read(-1)` wait until the client closes the connection, and that blocks the single-threaded server for everyone.
   - **Change in `app/server.py` `_read_json` (applies to every endpoint):** a `Content-Length` that is negative or not a number → `400`. Anything over **64 KiB** (65,536 bytes) → `413` `{"error": "Request body is too large"}`, without reading the body.
   - **Change in `app/service.py`:** module constants `MAX_NAME = 200`, `MAX_URL = 2048` and `MAX_DESCRIPTION = 2000` characters, checked after trimming. Anything longer → `400`. These are security limits chosen to be generous; the PO may tune the numbers. TASK-003's `update_description` should use the same `MAX_DESCRIPTION`.
3. **409 reveals that a URL is registered: accepted, no change.** It follows directly from the PO's "duplicates across all users" decision and is already listed under Risks.
4. **Out of scope, noted:** `X-User` is a claim, not authentication, so anyone can act as any user. That's how the app works today and isn't part of TASK-001.

**Tests:** DEVELOPER adds tests for a URL with credentials → 400 and nothing stored; an oversized field → 400; a body over 64 KiB → 413; a negative `Content-Length` → 400. QA's `tests/test_qa_task001.py` currently records the risky behaviour (`test_risk_*`); QA owns those tests and will turn them around on the next pass.
