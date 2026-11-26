# QA: TASK-002

## Attempt

1

## Checks from the acceptance criteria

| Criterion | My test (in `tests/test_qa_task002.py`) | Result | Evidence |
|---|---|---|---|
| AC1 | `test_ac1_owner_removes_and_it_leaves_their_list` | PASS | Repository 1 no longer in alice's list |
| AC2 | `test_ac2_gone_everywhere_including_analysis`, `test_http_delete_is_204_empty_then_404` | PASS | Get, analysis and scan raise `NotFound`; analysis entry removed; over HTTP `204` with empty body, then `404` on all four routes |
| AC3 | `test_ac3_removal_survives_restart_and_reset_restores_seed` | PASS | A second `Store` on the same file has no repository 1 or its analysis; `reset=True` brings the seed back |
| AC4 | `test_ac4_other_users_repository_is_denied_and_unchanged`, `test_http_wrong_user_and_unknown_user` | PASS | bob gets `Forbidden` / `403`; repositories, analyses and `next_id` unchanged |
| AC5 | `test_ac5_unknown_user_and_absent_repository`, `test_http_wrong_user_and_unknown_user` | PASS | `Unauthorized` / `401` for mallory; `NotFound` for id 999; nothing changed |
| AC6 | `test_ac6_failed_save_reports_failure_and_changes_nothing`, `test_ac6_other_repositories_and_analyses_unchanged` | PASS | With `os.replace` forced to fail: `StorageError` (500), memory and file unchanged, no temp file left. Removing 1 leaves every other repository and analysis identical |

Command: `python -m unittest tests.test_qa_task002 -v` printed `Ran 13 tests ... OK`. Whole suite: `python -m unittest` printed `Ran 78 tests ... OK`.

## Code review

Reviewed `service.remove_repository`, `service._commit` and `Store.commit` / `_save` / `load` against `architecture.md`. Checks reuse `_get_owned` (401, 404, 403) before anything changes; the new state is saved atomically (temp file + `os.replace`) before memory is swapped; `next_id` is kept, so ids are never reused. No defects found.

Notes for the Product Owner and SECURITY, not blocking this task:

- Persistence means TASK-001's open security finding (credentials in URLs) now also lands in `data/registry.json` in plain text. It is reported on TASK-001, so it isn't repeated here.
- As `architecture.md` says, registrations and scans now survive a restart. That's a visible change the Product Owner should know about.

## Other checks

- Wrong input: removing an id twice gives `NotFound` (`test_removing_twice_is_not_found`); a corrupt data file stops start-up with `DataFileError` instead of reseeding (`test_corrupt_data_file_stops_instead_of_reseeding`).
- Worked before: alice's list is unchanged without a removal (`test_worked_before_listing_still_works`).
- Ids are never reused, even after a restart (`test_removed_id_is_never_reused_even_after_restart`).

## Verdict

All six acceptance criteria PASS. Routed to SECURITY before the Product Owner: this task adds the first on-disk storage of registry data, which needs a security review.

## Failure type

`SECURITY_RISK`: not a broken criterion, but security-relevant behaviour that only SECURITY can accept or ask to change:

1. All registry data (users, repositories, analyses) is written in plain text to `data/registry.json` (`Store._save`); nothing restricts who can read the file.
2. `403` on `DELETE` of another user's repository tells them that the id exists, while a missing id gives `404` (`test_http_wrong_user_and_unknown_user`). The design keeps this for consistency; SECURITY should confirm.
3. Nothing locks the data file, so two server processes on the same file would overwrite each other's changes (noted in `implementation.md`).

If SECURITY accepts these, the task can go straight back to `READY_FOR_QA` → `READY_FOR_PO`; no code change is needed for the acceptance criteria.
