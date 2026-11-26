# QA: TASK-003

## Attempt

1

## Checks from the acceptance criteria

| Criterion | My test (in `tests/test_qa_task003.py`) | Result | Evidence |
|---|---|---|---|
| AC1 | `test_ac1_owner_updates_and_next_read_shows_it`, `test_http_patch_returns_200_with_full_repository` | PASS | New description returned and shown on the next `GET`; HTTP `200` body equals `GET /repositories/1` |
| AC2 | `test_ac2_empty_string_and_null_are_allowed`, `test_ac2_bad_bodies_rejected_and_nothing_changes` | PASS | `""` and `null` accepted; 8 bad bodies (not an object, `{}`, number, list, extra `name` / `owner` keys) raise `Invalid`, store unchanged |
| AC3 | `test_ac3_unknown_user_non_owner_and_missing_repository`, `test_http_error_codes` | PASS | 401 mallory, 403 bob (also with an invalid body, so access is checked first), 404 id 999; nothing changed |
| AC4 | `test_ac4_only_the_description_changes` | PASS | All other fields and repositories identical; analyses and `next_id` unchanged |
| AC5 | `test_ac5_file_backed_change_survives_restart`, `test_ac5_failed_save_reports_error_and_changes_nothing` | PASS | A second `Store` on the same file shows the change; with `os.replace` failing: `StorageError` (500), memory and file unchanged |

Command: `python -m unittest tests.test_qa_task003 -v` printed `Ran 12 tests ... OK`. One QA run, as agreed with the team.

## Code review

Reviewed `service.update_description` (commit `d6bb1a1`, plus the description limit added by TASK-001 attempt 2) against `architecture.md`. Access is checked before the body, only `description` can be written, and saving goes through the existing save-first `_commit`. The 2,000-character description limit also applies here (`test_description_limit_also_applies_to_update`). No defects found.

## Other checks

- Wrong input: covered in AC2 and the limit test (2,001 characters rejected, 2,000 accepted).
- Worked before: alice's repository description is unchanged without an update (`test_worked_before_detail_unchanged_without_update`).
- Works on a repository registered through TASK-001 (`test_works_on_a_newly_registered_repository`).

## Verdict

All five acceptance criteria PASS. Routed to SECURITY before the Product Owner: this is a new endpoint that changes stored data, and it needs a security review.

## Failure type

`SECURITY_RISK`: not a broken criterion, but security-relevant behaviour that only SECURITY can accept or ask to change:

1. The description is stored exactly as sent, with no sanitising, so it can hold HTML or script text. The API only returns JSON today, but any page that shows descriptions would have to escape them.
2. `403` for another user's repository and `404` for a missing one let any user find out which ids exist (same rule as TASK-002).
3. There's no version check, so the last write wins if two updates happen close together.

If SECURITY accepts these, the task can go back through `READY_FOR_QA` to `READY_FOR_PO`; no code change is needed for the acceptance criteria.
