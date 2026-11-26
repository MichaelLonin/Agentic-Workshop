# Architecture: TASK-004

<!-- Owner: ARCHITECT. Security notes: SECURITY. A few bullets, not a design document. -->

## Approach

- This is a small fix in the HTTP layer. `Handler._dispatch` in `app/server.py` already collects the methods of every route whose path matches, in `allowed`. Send that same list in an `Allow` header on the 405 response.
- Build the value once: `allow = ", ".join(sorted(set(allowed)))`. Use it for the new header and in the existing error body, which already uses exactly this expression, so the body stays byte-for-byte the same (AC5).
- Give `_send` an optional `headers=None` argument (a dict) that it writes before `end_headers()`. Only the 405 branch passes it; every other call stays as it is (AC5).
- Because the list is built from the `ROUTES` table and not hard-coded, it is always "all and only" the methods registered for that path (AC1). New endpoints (e.g. TASK-003's `PATCH`) appear in it automatically.
- Query strings and trailing slashes are already removed before matching (`urlsplit` and `rstrip("/")`), so AC4 needs no extra work. Just cover it with a test.

## Parts that change

- `app/server.py`: `_send(status, payload, headers=None)`; the 405 branch of `_dispatch`.
- `docs/api.md`: one line saying that a 405 response carries an `Allow` header.
- `tests/test_api.py`: AC2–AC4 checks on the `Allow` header, compared as a set of method names (the order isn't specified), plus an assertion that the 405 body is unchanged.
- Not changed: `app/service.py`, `app/store.py`, storage and restart behaviour.

## Interface

- **Response to a wrong method on a known path:** `405`, header `Allow: <METHOD>, <METHOD>` (comma-and-space separated, alphabetical, no duplicates), and the unchanged body `{"error": "<METHOD> is not allowed here. Allowed: <same list>"}`.
- Examples with today's routes: `PUT /health` → `Allow: GET`; `PUT /repositories` → `Allow: GET, POST`; `POST /repositories/1` → `Allow: DELETE, GET`; `PUT /repositories/1/analysis` → `Allow: GET`; `PUT /repositories/1/scan` → `Allow: POST`.
- An unknown path is still `404` with no `Allow` header.

## Risks and limits

- **Overlap with TASK-003 (flag for BA/QA):** TASK-003 adds `PATCH /repositories/{id}`. Once that is built, `POST /repositories/1` correctly answers `Allow: DELETE, GET, PATCH`. That follows AC1 ("all and only the methods supported") and the PO decision ("the methods actually supported"), but it no longer matches the literal list in AC3 ("`GET` and `DELETE`"). The design is the same either way. The PRODUCT_BA may want to reword AC3's example so QA doesn't fail it because of the order the tasks were built in.
- `HEAD` and `OPTIONS` still get Python's default `501`, because the handler doesn't define them. They aren't part of this request, so `Allow` doesn't list them.
- The header is sorted alphabetically for stable tests; clients must not depend on the order.

## Security notes

- None reported. The header only exposes method names that the 405 body already shows today.
