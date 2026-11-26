# Requirements: TASK-005

## The request in one sentence

GET requests must ignore their request body so the health monitor can check the API successfully.

## Acceptance criteria

- **AC1:** Given the API is running, when `GET /health` is sent without a body, it returns 200 and `{"status": "ok"}`.
- **AC2:** Given the API is running, when `GET /health` is sent with a small body containing valid JSON, malformed JSON, or non-JSON text, each request returns the same 200 response and payload as a request without a body.
- **AC3:** For the other existing GET endpoints, a request with a body produces the same status and response as the equivalent request without a body, including normal access and not-found errors; the body does not change stored data.
- **AC4:** Existing behavior for non-GET methods remains unchanged, including rejection of invalid JSON for endpoints that accept a body. Stored data and restart behavior remain unchanged.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- **Delegated Product Owner decision:** Apply the request to all GET endpoints, not only `/health`, because Business states that GET requests should not care about a body. Retain the existing health response and non-GET behavior to keep the fix within scope.

## Out of scope

- Changes to storage, restart behavior, or non-GET endpoint functionality.

## Product Owner decision

- Pending acceptance.
