# Repository registry API

The sample app keeps a list of code repositories that users have registered, and a pretend analysis of each one. It's a small JSON API built only on the Python standard library, so there's nothing to install.

- **Code:** `app/service.py` has the business logic, `app/server.py` the HTTP endpoints, `app/store.py` the data, and `app/analyzer.py` the pretend analysis.
- **Data:** `python -m app.server` saves every change to `data/registry.json` (change it with `--data PATH`), so registrations, scans and removals survive a restart. `python -m app.server --reset`, or deleting the file, goes back to the seed data in `app/store.py`. If the file can't be read, the server refuses to start instead of quietly reseeding. Tests use an in-memory store and write nothing.
- **Who is calling:** send the header `X-User: <username>`. Without it, you are `alice`. Known users are `alice`, `bob` and `chen`.
- **Access:** a user can only see and use repositories they own.

## Endpoints today

| Method and path | What it does | Errors |
|---|---|---|
| `GET /health` | Returns `{"status": "ok"}` | |
| `GET /repositories` | Lists your repositories: `id`, `name`, `url`, `owner` | 401 unknown user |
| `POST /repositories` | Registers a repository you own. Body: `name`, `url` (absolute http or https), optional `description`. Returns 201 and the new repository; its analysis is ready straight away | 400 invalid body, 401, 409 URL already registered |
| `GET /repositories/{id}` | One repository, with `description`, `registered_at` and `last_scanned_at` | 401, 403 not yours, 404 |
| `DELETE /repositories/{id}` | Removes one of your repositories and its analysis, at once and for good. Returns 204 and no body; the id is never reused | 401, 403 not yours, 404, 500 couldn't be saved (nothing changed) |
| `GET /repositories/{id}/analysis` | The latest analysis: languages, files, lines of code, open findings, health score, contributors, summary | 401, 403, 404 |
| `POST /repositories/{id}/scan` | Runs the analysis again now and returns it | 401, 403, 404 |

Errors come back as `{"error": "<message>"}`.

## Seed data

| id | name | owner |
|---|---|---|
| 1 | payments-api | alice |
| 2 | web-portal | alice |
| 3 | data-pipeline | bob |
| 4 | mobile-app | chen |

## Try it

```
python -m app.server
```

Then, in another terminal:

```
curl http://localhost:8000/repositories
curl -H "X-User: bob" http://localhost:8000/repositories
curl -X POST http://localhost:8000/repositories/1/scan
```

In Windows PowerShell, use `curl.exe` instead of `curl`.

## Adding an endpoint

1. Put the logic in `app/service.py`. Raise `Invalid`, `Forbidden` or `NotFound` for errors.
2. Add a small handler in `app/server.py` with the `@route("METHOD", r"/path")` decorator. The request's JSON body is in `req.body`, and the query string in `req.query`.
3. Add tests in `tests/`. Run them with `python -m unittest`.
