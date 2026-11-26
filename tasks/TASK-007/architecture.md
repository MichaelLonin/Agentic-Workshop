# Architecture: TASK-007

<!-- Owner: ARCHITECT. Security notes: SECURITY. A few bullets, not a design document. -->

## Approach

- Add `POST /repositories/scan`. The logic goes in a new `service.scan_all_repositories(store, username)`, plus a thin `@route` handler in `server.py` that returns `200`. The path doesn't clash with `/repositories/(\d+)/scan`, because those routes only match digits.
- Check the caller with `require_user` (401) before anything else (AC4). Pick the caller's repositories in the same way as `list_repositories`: `owner == username`, sorted by id.
- **All-or-nothing (AC5):** take one `scanned_at = now_utc()`. For each owned repository, build `updated = {**repo, "last_scanned_at": scanned_at}` and `analyzer.analyze(updated, scanned_at)` into *new* dicts, without touching the store. Then save everything with **one** call to `_commit(store, repositories, analyses, store.next_id)`. If any analysis raises, or the save fails, nothing has been swapped in yet, so memory and the file both stay as they were.
- Pull the per-repository step out of `scan_repository` into a small shared helper (e.g. `_rescan(repo, scanned_at)` → `(updated, analysis)`) and use it in both functions, so a bulk scan gives exactly the same result as single scans (PO decision). `scan_repository`'s behaviour doesn't change.
- **No repositories (AC3):** return `[]` without calling `_commit`, so nothing is written.

## Parts that change

- `app/service.py`: the `_rescan` helper, `scan_all_repositories`, and `scan_repository` refactored to use `_rescan`.
- `app/server.py`: add `@route("POST", "/repositories/scan")`.
- `docs/api.md`: add a row for the new endpoint.
- `tests/`: several repositories scanned once with the same new timestamp; another user's data unchanged and not returned; a user with no repositories → `[]` and the data file not rewritten; unknown user → 401; `analyzer.analyze` patched to fail on the 2nd repository → 500 and nothing changed; `os.replace` patched to fail → 500 and nothing changed; a restart with a file-backed store keeps the results.

## Interface

- **Request:** `POST /repositories/scan`, header `X-User: <username>`, no body needed (any body is ignored).
- **Success:** `200`, a JSON list sorted by repository id. Each item is `{"repository": {"id", "name", "url", "owner"}, "analysis": {<same shape as GET /repositories/{id}/analysis>}}`. A user with no repositories gets `[]`.
- **Errors** (all `{"error": "<message>"}`, nothing changed):
  - `401`: unknown user.
  - `500`: a scan or the save failed. A save failure is the existing `StorageError`. For a scan failure, add a `ScanError(ServiceError)` with `status = 500` and the message "Bulk scan failed, so nothing was changed", raised by catching exceptions from `analyze` inside the loop.

## Risks and limits

- The response is as large as the caller's repository count, with no paging. That's fine at workshop scale; paging would be a separate request.
- Every repository in a bulk scan gets the same `last_scanned_at`. That's deliberate: it shows they belong to one review run.
- `GET /repositories/scan` will return `405` with `Allow: POST` through TASK-004's routing, which is correct.
- Builds on TASK-002's `_commit`/`StorageError` and TASK-001's error classes, which are both still in QA. If those change, this design follows them.

## Security notes

- None reported. The endpoint takes no input apart from the caller and only ever reads or writes the caller's own repositories.
