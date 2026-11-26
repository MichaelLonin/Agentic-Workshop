# Implementation: TASK-002

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real implementation, not a stub, following `architecture.md`.

- **`DELETE /repositories/{id}`** → `204`, empty body. The checks come from `_get_owned`, so: unknown user 401, no such id 404, someone else's 403. The repository and its analysis are removed together, and nothing else changes. `next_id` isn't touched, so an id is never reused and stays 404.
- **Persistence (AC3).** `Store(path=None, reset=False)`. With no path (the default, used by every test) it works in memory exactly as before. With a path, it loads the JSON file if it exists, otherwise it starts from the seed data and saves it. `python -m app.server` uses `data/registry.json`; `--data PATH` changes that and `--reset` starts from the seed data and overwrites the file.
- **Save first, then change memory (AC6).** Every change (register, scan and remove) builds the new state, then `store.commit()` writes it atomically (a temp file in the same folder, then `os.replace`), and only then swaps it into memory. If the write fails, the API returns `500` and memory and the file are both unchanged; the temp file is deleted.
- **Unreadable data file:** the server refuses to start with a clear message ("Fix or delete it, or start with --reset…") instead of quietly reseeding.

## Files changed

- `app/store.py`: `DataFileError`, `Store(path, reset)`, `load()`, `commit()`, atomic `_save()`. `reset()` now goes through `commit()`.
- `app/service.py`: `StorageError` (500), `_commit()`, `remove_repository()`. `register_repository()` and `scan_repository()` now build the new state and commit it, instead of changing memory in place.
- `app/server.py`: route `DELETE /repositories/{id}`; `--data` and `--reset`; a clear exit if the data file can't be read.
- `.gitignore`: `data/`.
- `docs/api.md`: the new endpoint, and how data is now saved and reset.
- `tests/test_service.py`: 3 tests (removal, denied without changes, other repositories unchanged and the id never reused).
- `tests/test_store.py` (new): 6 tests (no file without a path, removal survives a restart, register and scan survive a restart, reset, a failed save changes nothing, an unreadable file stops).
- `tests/test_api.py`: 2 HTTP tests (204 then 404 everywhere; 403 and 401 change nothing).

## Tests

- `python3 -m unittest` → `Ran 44 tests ... OK` (33 before, plus 11 new).
- By hand, a real server with `--data` in a temp folder: `DELETE /repositories/1` → 204; after a restart `GET /repositories/1` → 404 and alice's list is `[2]`; after `--reset` → 200; with a file containing `not json`, the server stops with the message above.

## Known limits

- As `architecture.md` says, TASK-001 registrations and the latest scan results now also survive a restart. That's a visible change the PO should know about.
- Only one server process should use a given data file. Nothing locks it.
- A 403 for another user's repository tells them the id exists. This is the existing rule, kept for consistency.
- Seed users are saved in the file too. They don't change at run time.

## Attempts

- Attempt 1: first version.
