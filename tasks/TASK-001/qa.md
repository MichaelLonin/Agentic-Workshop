# QA: TASK-001

## Attempt

1

## Checks from the acceptance criteria

| Criterion | My test (in `tests/test_qa_task001.py`) | Result | Evidence |
|---|---|---|---|
| AC1 | `test_ac1_created_with_values_and_owned_by_caller` | PASS | Name and URL trimmed, owner is the caller |
| AC2 | `test_ac2_description_optional` | PASS | Description kept; `null` when absent |
| AC3 | `test_ac3_wrong_input_rejected_and_nothing_created` | PASS | 6 bad bodies raise `Invalid`, store unchanged |
| AC4 | `test_ac4_owner_sees_it_and_another_user_cannot` | PASS | Listed for owner; `Forbidden` for alice |
| AC5 | `test_ac5_analysis_available_at_once` | PASS | Analysis returned without a scan |
| AC6 | `test_ac6_duplicate_url_rejected_across_users` | PASS | `Conflict` for another user's URL with spaces; count unchanged |

Command: `python -m unittest tests.test_qa_task001 -v` printed `Ran 10 tests ... OK`. Whole suite: `python -m unittest` printed `Ran 54 tests ... OK`.

## Code review

Reviewed commit `8b790c6` (`app/service.py`, `app/server.py`) against `requirements.md` and `architecture.md`. The code follows the design: user check, then validation, then duplicate check, then write. Security findings, each backed by a test that records today's behaviour:

1. **Credentials in the URL are stored and returned** (`test_risk_credentials_in_url_are_stored_and_returned`). `https://user:TOKEN@github.com/org/private` passes `_is_web_url`, is stored as-is and is returned by `POST` and `GET /repositories/{id}`. With the JSON snapshot from TASK-002, the token is also written to disk in plain text. Nothing in the requirements or design covers secrets in URLs.
2. **No size limits** (`test_risk_no_length_limit_on_fields`). A 2,000,000-character name and description are accepted and kept. `server.py` reads the body by `Content-Length` with no cap, and every registration stays in the store, so one user can grow memory (and the data file) without limit. `architecture.md` notes "no length limits" but doesn't assess it as a security risk.
3. **409 reveals that a URL is registered** (`test_risk_conflict_reveals_another_users_url`). Another user can probe whether a given URL exists. This is a Product Owner decision (duplicates across all users) and is already noted in `architecture.md`, so it is recorded, not blocking.

## Other checks

- Wrong input: covered in AC3 (blank name, missing name, `null` URL, `ftp:` URL, relative URL, `https://` with no host).
- Worked before: `test_existing_seed_repositories_still_work`, seed repositories still listed for alice.

## Verdict

FAILED. All six acceptance criteria pass, but findings 1 and 2 are security risks that need SECURITY's judgment before the Product Owner sees this.

## Failure type

`SECURITY_RISK`: the code meets the requirements, but it stores and returns credentials embedded in URLs (also written to disk), and has no size limits on a request whose data is kept forever. SECURITY decides whether the code must change (then `READY_FOR_DEVELOPMENT`) or the risks are accepted (then `READY_FOR_QA`).
