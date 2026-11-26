# Architecture: TASK-005

<!-- Owner: ARCHITECT. Security notes: SECURITY. A few bullets, not a design document. -->

## Approach

- The bug is in `Handler._dispatch` (`app/server.py`): it calls `_read_json()` for every method, so the body of a GET is parsed as JSON and a bad body returns 400 before the handler runs.
- Split reading from parsing. A new `_read_body()` returns the raw bytes (or `None` when there is no body) and applies the TASK-001 security checks on `Content-Length`. `_read_json()` becomes `_read_body()` plus `json.loads`.
- In `_dispatch`, a GET calls `_read_body()` and **throws the bytes away**, with `body = None`. It never parses them, so the request runs exactly as if it had no body (AC1–AC3). The body is still read off the connection, so the client doesn't get a reset instead of the response.
- Every other method keeps calling `_read_json()` unchanged, so a bad JSON body is still `400 Body is not valid JSON` (AC4).
- GET handlers never use `req.body` today. Setting it to `None` also guarantees that a GET body can't reach stored data (AC3).

## Parts that change

- `app/server.py`: a new `_read_body()`, `_read_json()` built on top of it, and one branch in `_dispatch` (`if method == "GET"`).
- `docs/api.md`: one line saying that GET requests ignore any body.
- `tests/test_api.py`: `GET /health` with no body, a valid JSON body, malformed JSON and plain text → the same 200 and `{"status": "ok"}`. `GET /repositories/1` with a body → 200; `GET /repositories/999` with a body → 404; `GET /repositories/3` as alice with a body → 403. `POST /repositories` with malformed JSON → still 400.
- Not changed: `app/service.py`, `app/store.py`, storage and restart behaviour.

## Interface

- No new endpoints. **All** GET endpoints: any body with a valid `Content-Length` of up to 64 KiB is read and ignored, and the response is the same as with no body.
- Non-GET endpoints: unchanged.

## Risks and limits

- **Fits with TASK-001 attempt 2 (same function, same developer):** TASK-001's security fix adds the `Content-Length` checks (negative or not a number → 400, over 64 KiB → 413) to the body reader. Those checks belong in `_read_body()`, so they apply to GET as well. A GET with an absurd or oversized `Content-Length` therefore still gets 400 or 413 and never makes the server wait. The requirements only cover a *small* body, so this doesn't conflict with them. Whichever task is built first, both should end up in `_read_body()`.
- A body sent with `Transfer-Encoding: chunked` (no `Content-Length`) is not read for any method, which is the existing behaviour.
- `HEAD` and `OPTIONS` are still not handled (Python's default 501), which is outside this task.

## Security notes

- None reported. Ignoring GET bodies takes away a parsing step, so it doesn't add any attack surface. The size and length checks from TASK-001 still apply before anything is read.
