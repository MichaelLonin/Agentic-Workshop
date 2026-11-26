# Implementation: TASK-007

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real implementation, not a stub, following `architecture.md`. `POST /repositories/scan` → `200` and a list sorted by id of `{"repository": {id, name, url, owner}, "analysis": {...}}`.

- `require_user` first, so an unknown user gets 401 and nothing changes (AC4). Then the caller's repositories, chosen the same way as `list_repositories`.
- **All or nothing (AC5):** one `scanned_at` for the whole run. Each repository is rescanned into new dicts, with the store untouched. Then **one** `_commit()` saves everything.
  - Any exception from the analyser becomes `ScanError` (500, "Bulk scan failed, so nothing was changed").
  - A failed save is the existing `StorageError` (500).
  - Either way, memory and the data file are unchanged.
- **No repositories (AC3):** returns `[]` without calling `_commit`, so nothing is written.
- New `_rescan(repo, scanned_at)` helper, which `scan_repository` now uses too. A bulk scan gives exactly the same result as single scans, and `scan_repository`'s behaviour is unchanged.

## Files changed

- `app/service.py`: `ScanError` (500), `_rescan()`, `scan_all_repositories()`, and `scan_repository()` built on `_rescan()`.
- `app/server.py`: route `POST /repositories/scan`. It doesn't clash with `/repositories/{id}/scan`, which only matches digits.
- `docs/api.md`: one row for the new endpoint.
- `tests/test_service.py`: 4 tests.
  - Each owned repository is scanned exactly once (the analyser call count is 2 for alice), with one timestamp, and the store matches the response. Other users' data is unchanged and not returned.
  - No repositories gives `[]` and nothing changes.
  - An unknown user gets 401 and nothing changes.
  - The analyser failing on the 2nd repository gives `ScanError` 500 and nothing changes.
- `tests/test_store.py`: 3 tests (survives a restart; a failed save changes memory and file not at all; nothing to scan means no save is attempted).
- `tests/test_api.py`: 2 tests (200 with list and matching analyses; 401, `GET /repositories/scan` → 405 `Allow: POST`, single scan still works).

## Tests

- `python3 -m unittest tests.test_service tests.test_api tests.test_store tests.test_analyzer tests.test_new_task` → `Ran 77 tests ... OK`.
- Whole suite: `Ran 100 tests ... FAILED (errors=2)`. These are the same 2 expected errors as before: QA's TASK-001 `test_risk_*` tests record the behaviour that TASK-001 attempt 2 removed. They're QA-owned, and I didn't change them. Nothing in TASK-007 fails.

## Known limits

- A valid JSON body is ignored. A **malformed** body still gets `400 Body is not valid JSON`, like every other POST (TASK-005 kept that for non-GET methods).
- No paging; all repositories in one run share `last_scanned_at`, as designed.

## Attempts

- Attempt 1: first version.
