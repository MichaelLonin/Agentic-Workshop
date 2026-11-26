# Architecture: TASK-003

<!-- Owner: ARCHITECT. Security notes: SECURITY. A few bullets, not a design document. -->

## Approach

- Add `PATCH /repositories/{id}`, with `description` as the only field that can be changed. The logic goes in a new `service.update_description(store, username, repository_id, body)`, plus a thin `@route` handler in `server.py` that returns `200`.
- Check access first with the existing `_get_owned`: 401 unknown user, 404 no such id, 403 not the owner (AC3). Validate the body only after that, so a non-owner never learns anything from validation messages.
- Validate, then build the new state in the same way as `scan_repository`: `updated = {**repo, "description": new}`, `repositories = {**store.repositories, id: updated}`. Save it with the existing `_commit(store, repositories, store.analyses, store.next_id)`. A failed save raises the existing `StorageError` (500) and nothing changes (AC5).
- Pass `store.analyses` through unchanged and don't touch `last_scanned_at` or any other field, so the analysis isn't re-run or changed (AC4). Don't add an "updated at" field, because the requirements don't ask for one.

## Parts that change

- `app/service.py`: add `update_description`. Reuse `_get_owned`, `_commit`, `Invalid` and `StorageError`; nothing new in the store.
- `app/server.py`: add `@route("PATCH", r"/repositories/(\d+)")`. `do_PATCH` already exists.
- `docs/api.md`: add a row for the new endpoint.
- `tests/`: tests for AC1–AC5, including a failed save (patch `os.replace` as in TASK-002) and a restart with a file-backed `Store`.
- Not changed: `app/store.py`, `app/analyzer.py`.

## Interface

- **Request:** `PATCH /repositories/{id}`, header `X-User: <username>`, JSON body `{"description": <string or null>}`.
  - The `description` key must be present (an omitted key must never clear it). A string is stored as sent, including `""`, with no trimming, matching registration; `null` clears it.
  - The body must be a JSON object containing exactly the key `description`. Any other key (e.g. `name`, `url`, `owner`) is rejected rather than silently ignored, so nobody thinks they renamed a repository or changed its owner.
- **Success:** `200`, the full repository in the same shape as `GET /repositories/{id}`, with the new `description`.
- **Errors** (all `{"error": "<message>"}`, nothing changed), checked in this order:
  - `401`: unknown user.
  - `404`: no repository with that id.
  - `403`: the repository belongs to another user.
  - `400`: the body is missing or isn't a JSON object, `description` is missing, `description` is neither a string nor null, or there are any other keys.
  - `500`: the change couldn't be saved.

## Risks and limits

- This design builds on the TASK-002 storage code (`_commit`, `StorageError`, the file-backed `Store`), which is still waiting for QA. If QA sends TASK-002 back with storage changes, this design follows whatever `_commit` becomes; the approach stays the same.
- Rejecting extra keys is stricter than registration, which ignores unknown keys. It's a deliberate guard against "I thought I renamed it", and it's easy to loosen later.
- There are no length limits on descriptions, as before. The requirements don't ask for any.
- Only one write happens at a time (single-threaded server), so "last write wins" is the only kind of concurrency, and there's no version check.

## Security notes

- None reported. Ownership is checked before the body is validated, and only `description` can be written, so `owner`, `url` and `id` can't be changed through this endpoint.
