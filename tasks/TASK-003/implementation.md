# Implementation: TASK-003

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real implementation, not a stub, following `architecture.md`. `PATCH /repositories/{id}` with the body `{"description": <string or null>}` → `200` and the full repository, in the same shape as `GET /repositories/{id}`.

- **Access first** (`_get_owned`): 401 unknown user, 404 no such id, 403 not yours. A non-owner gets 403 even if the body is invalid.
- **Then the body:** 400 if it isn't a JSON object, if `description` is missing, if there are any other keys (the message names them), or if `description` isn't a string or `null`. A string is stored exactly as sent, including `""`; `null` clears it.
- **Only the description changes.** The new state is `{**repo, "description": …}`, and `store.analyses` is passed through as it is. That means no re-analysis, no change to `last_scanned_at`, and no other repository touched.
- **Saving** goes through the TASK-002 `_commit` (save first, then change memory). A failed save → 500 and nothing changes; with a data file, the change survives a restart.

## Files changed

- `app/service.py`: `update_description()`.
- `app/server.py`: route `PATCH /repositories/{id}`.
- `docs/api.md`: one row for the new endpoint.
- `tests/test_service.py`: 4 tests (only the description changes, empty and `null` allowed, bad bodies change nothing, access checked before the body).
- `tests/test_store.py`: 2 tests (survives a restart, a failed save changes nothing).
- `tests/test_api.py`: 2 HTTP tests (200 with the analysis unchanged; 403, 401, 404, 400 for other keys and 400 for no body, with nothing changed).

## Tests

`python3 -m unittest` → `Ran 52 tests ... OK` (44 before, plus 8 new).

## Known limits

- This builds on TASK-002's storage code, which is still waiting for QA. If QA sends TASK-002 back with storage changes, this follows whatever `_commit` becomes.
- Other keys are rejected (stricter than registration), as designed. There are no length limits, and the last write wins.

## Attempts

- Attempt 1: first version.
