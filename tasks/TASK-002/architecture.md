# Architecture: TASK-002

<!-- Owner: ARCHITECT. Security notes: SECURITY. A few bullets, not a design document. -->

## Approach

- Add `DELETE /repositories/{id}`. The logic goes in a new `service.remove_repository(store, username, repository_id)`, plus a thin `@route` handler in `server.py` that returns `204` with no body.
- Use the existing `_get_owned` for the checks, in its current order: unknown user → 401, no such id → 404, not the owner → 403. Nothing is changed before these pass (AC4, AC5).
- **Persistence for AC3.** `Store` gets an optional `path`. With no `path` (the default, which all tests use) it behaves exactly as it does today. With a `path`, it loads its state from that JSON file at start-up if the file exists, otherwise it starts from the seed data. It saves a snapshot after each change. `python -m app.server` passes `data/registry.json`.
- **Save first, then change memory (AC6).** Build the new state without the repository and its analysis, write it to disk atomically (temp file in the same folder, then `os.replace`), and only then remove the entries from `store.repositories` and `store.analyses`. If the write fails, raise a 500 error and leave memory and the file untouched. With no `path`, the in-memory removal is all there is.
- Removal deletes the repository and its analysis together and touches nothing else (AC6). Ids are never reused, because `next_id` is saved as well. That way a removed id always stays 404 (AC2), even after a restart.

## Parts that change

- `app/store.py`: `Store(path=None)`; `load` and atomic `save`. The snapshot holds `users`, `repositories`, `analyses` and `next_id`. Add a small helper, e.g. `store.commit(repositories, analyses, next_id)`, that saves first and then swaps in the new state. `reset()` restores the seed data and, if there is a `path`, saves it, which is the "explicit reset" in AC3.
- `app/service.py`: add a `StorageError(ServiceError)` with `status = 500`, and `remove_repository`. Change `register_repository` and `scan_repository` to go through the same save-then-commit helper, so the file never falls behind memory.
- `app/server.py`: add `@route("DELETE", r"/repositories/(\d+)")`, and add a `--data PATH` option (default `data/registry.json`) and a `--reset` flag that calls `store.reset()` at start-up.
- `.gitignore`: add `data/`, so runtime state is never committed.
- `docs/api.md`: add the new endpoint, and say that data now survives a restart and that `--reset` restores the seed data.
- `tests/`: removal, restart (build a second `Store` on the same temp file), a failed save (e.g. patch `os.replace` to raise), and that other repositories stay unchanged.

## Interface

- **Request:** `DELETE /repositories/{id}`, header `X-User: <username>`, no body.
- **Success:** `204`, empty body. After that, `GET /repositories/{id}`, `GET /repositories/{id}/analysis` and `POST /repositories/{id}/scan` all return `404`, and the id is gone from `GET /repositories`.
- **Errors** (all `{"error": "<message>"}`, nothing changed):
  - `401`: unknown user.
  - `404`: no repository with that id, including one that was already removed.
  - `403`: the repository belongs to another user. This matches the existing ownership rule; see Risks.
  - `500`: the change couldn't be saved; the repository and its analysis are still there and unchanged.

## Risks and limits

- **Side effect the PO should know about:** with persistence on, repositories registered through TASK-001 and the latest scan results now also survive a restart. Until now they were lost. This doesn't break any TASK-001 criterion, but it is a visible change. `--reset` (or deleting `data/registry.json`) brings back the seed data.
- If `data/registry.json` is unreadable or not valid JSON, the server must stop with a clear error at start-up rather than quietly reseeding. Quietly reseeding would bring removed repositories back.
- `403` for another user's repository tells them that the id exists. That's the existing behaviour for every endpoint, so it's kept for consistency. Hiding it (returning `404`) would be a separate product decision.
- The server is single-threaded, so there's no race between the checks, the save and the change in memory. Only one server process should use a given data file.
- Removal is permanent and has no confirmation or undo, as the PO decided.

## Security notes

- Design point: the data file path comes from the command line, never from a request, so a request can't steer where data is written.

### SECURITY review, attempt 1 (QA finding `SECURITY_RISK`, qa.md)

Reviewed `app/store.py` (`_save`, `load`), `app/server.py` (`--data`, `--reset`), `.gitignore` and `service._has_credentials`. **Verdict: all three findings accepted, no code change, back to QA.**

1. **Plain-text `data/registry.json`: accepted.** What it holds is demo users (name, demo email), repository names, URLs, descriptions and pretend analyses. There are no passwords or tokens: TASK-001 attempt 2 now rejects URLs with a username or password (`_has_credentials`), so secrets can't get into the file through registration. The file can't leak through Git either, because `data/` is in `.gitignore` and nothing under `data/` is tracked. The atomic save uses `tempfile.mkstemp`, which creates the file readable only by its owner on Linux/macOS (mode 0600, kept through `os.replace`); on Windows it inherits the folder's permissions. Encrypting a workshop demo file at rest would be out of proportion.
   - **Condition:** this depends on TASK-001's credential rejection shipping. If TASK-001 is rejected or that check is removed, reopen this item.
   - **Housekeeping:** a `data/registry.json` written *before* the TASK-001 fix could still hold a test URL with credentials. Start once with `--reset` (or delete the file) on any machine where that was tried.
2. **403 reveals that an id exists: accepted.** Ids are sequential small integers, so they're easy to guess anyway. `X-User` is a claim rather than authentication, so any caller can already act as the owner. Returning 404 here would hide nothing real, and it would make `DELETE` behave differently from `GET`, `PATCH` and `scan`. Changing this everywhere would be a separate product decision.
3. **No lock on the data file: accepted as a documented operational limit.** This is about integrity between *two* server processes (lost updates), not confidentiality, and it was already stated in Risks: "only one server process should use a given data file". Within one process the server is single-threaded and each save is atomic, so the file is never left half-written. Cross-platform file locking isn't worth adding for a workshop demo.
