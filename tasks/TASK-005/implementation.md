# Implementation: TASK-005

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real fix, not a stub, following `architecture.md`.

- `_read_body()` (new in `app/server.py`) returns the raw bytes or `None`. It applies the TASK-001 security checks on `Content-Length` first (not a number or negative → 400, over 64 KiB → 413), so those still apply to every method, GET included.
- `_read_json()` is now `_read_body()` plus `json.loads`, unchanged for non-GET methods. Bad JSON is still `400 Body is not valid JSON` (AC4).
- In `_dispatch`, a **GET** calls `_read_body()`, throws the bytes away unparsed, and runs with `body = None`. The response is exactly the same as with no body (AC1–AC3), and a GET body can never reach stored data. The body is still read off the connection, so the client gets the response, not a reset.

## Files changed

- `app/server.py`: `_read_body()`, `_read_json()` on top of it, and the GET branch in `_dispatch`.
- `docs/api.md`: one line saying GET ignores a body, and that every body is limited to 64 KiB.
- `tests/test_api.py`: 3 tests.
  - `GET /health` with a valid JSON body, malformed JSON, plain text and non-UTF-8 bytes gives the same 200 `{"status":"ok"}` as with no body.
  - Six GET cases (list, detail, analysis, 404, 403, and 401 for an unknown user), each sent with a body, give the same status and payload as without one, and the store is unchanged.
  - `POST /repositories` with `{not json` still gives 400 "not valid JSON".

## Tests

- `python3 -m unittest tests.test_service tests.test_api tests.test_store tests.test_new_task` → `OK`.
- Whole suite: `Ran 74 tests ... FAILED (errors=2)`. These are the same 2 expected TASK-001 errors as before: QA's `test_risk_*` tests in `tests/test_qa_task001.py` record the risky behaviour that TASK-001 attempt 2 removed. They're QA-owned, and I didn't change them. Nothing in TASK-005 fails.

## Known limits

- A GET with an absurd or oversized `Content-Length` still gets 400 or 413 (the TASK-001 security checks run before anything is read). The requirements cover only a small body, so this is intended, as `architecture.md` says.
- A body sent with `Transfer-Encoding: chunked` (no `Content-Length`) isn't read for any method, which is the existing behaviour.

## Attempts

- Attempt 1: first version.
