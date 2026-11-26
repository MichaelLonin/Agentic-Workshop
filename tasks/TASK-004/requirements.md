# Requirements: TASK-004

## The request in one sentence

Include the allowed methods in an `Allow` header when the API returns 405 for a wrong method.

## Acceptance criteria

- **AC1:** Given an existing endpoint and a method that currently receives 405, when it is called with that method, then the response remains 405 and includes an `Allow` header listing all and only the methods supported for that endpoint, as comma-separated HTTP method names.
- **AC2:** When `PUT /health` is called, the 405 response's `Allow` header lists `GET`; when `PUT /repositories` is called, it lists both `GET` and `POST`.
- **AC3:** When `POST /repositories/1` is called, the 405 response's `Allow` header lists `GET` and `DELETE`; for `PUT /repositories/1/analysis` it lists `GET`, and for `PUT /repositories/1/scan` it lists `POST`.
- **AC4:** Given a wrong-method request with a query string or a trailing slash, the 405 response lists the same allowed methods as the corresponding endpoint without them.
- **AC5:** Existing successful responses, 404 responses for unknown paths, and the existing 405 error body remain unchanged; storage and restart behavior remain unchanged.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- **Delegated Product Owner decision:** List the methods actually supported by the matched endpoint, with no requirement on their order, so clients can choose an available method.
- **Delegated Product Owner decision:** Apply the header to existing 405 responses and retain other response and persistence behavior; the request does not call for adding methods or changing storage.

## Out of scope

- Adding endpoints or changing which methods an endpoint supports.

## Product Owner decision

- Pending acceptance.
