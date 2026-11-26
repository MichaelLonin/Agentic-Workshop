# Implementation: TASK-004

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real fix, not a stub, following `architecture.md`. A `405` now has an `Allow` header. Its value is built from the `ROUTES` table for the matched path (`", ".join(sorted(set(allowed)))`), so it is always all and only the methods that path supports. The same string is used in the existing error body, which stays byte-for-byte the same. `_send()` gained an optional `headers` argument; only the 405 branch uses it.

## Files changed

- `app/server.py`: `_send(status, payload, headers=None)`; the 405 branch sends `Allow`.
- `docs/api.md`: one sentence saying a 405 has an `Allow` header.
- `tests/test_api.py`: 3 tests (the header and unchanged body for all five AC2/AC3 cases; query string and trailing slash; no `Allow` on a 404 or a 200).

## Tests

- `python3 -m unittest` → `Ran 55 tests ... OK` (52 before, plus 3 new).
- By hand: `curl -i -X PUT localhost:8766/repositories` → `405` with `Allow: GET, POST`.

## Known limits

- **AC3 and TASK-003, flagged for QA and the BA (the Architect raised it too):** `PATCH /repositories/{id}` from TASK-003 is already built, so `POST /repositories/1` answers `Allow: DELETE, GET, PATCH`, not just "`GET` and `DELETE`" as AC3's example says. I followed AC1 ("all and only the methods supported") and the PO decision ("the methods actually supported"), and my test expects `PATCH` too. If the BA rewords AC3, no code change is needed.
- `HEAD` and `OPTIONS` still get Python's default `501` and aren't listed. That's out of scope.
- The header is sorted alphabetically; clients shouldn't depend on the order.

## Attempts

- Attempt 1: first version.
