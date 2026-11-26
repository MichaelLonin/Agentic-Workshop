# Implementation: TASK-006

<!-- Owner: DEVELOPER. Be honest: QA won't take your word for it anyway. -->

## What I built

A real fix, not a stub, following `architecture.md`. `app/analyzer.py` has a new pure helper, `findings_text(count)`: `"1 open finding"` for 1, `f"{count} open findings"` otherwise. The summary line uses it: `f"{files} files, mostly {main_language}. {findings_text(open_findings)}."`. Nothing else in `analyze()` changed: not the numbers, not the fields, not the rest of the text. Registration and scan both call `analyze()`, so both get the new wording. Stored analyses aren't touched (AC5).

## Files changed

- `app/analyzer.py`: `findings_text()` and the summary line.
- `tests/test_analyzer.py` (new): 4 tests.
  - `findings_text` for 0, 1, 2 and 11.
  - The summary ending for real URLs whose hash gives exactly 0, 1 and 2 findings.
  - Only the one word changed, compared against the old format.
  - Registration and rescan both say `1 open finding.`

## Tests

- `python3 -m unittest tests.test_analyzer` → `Ran 4 tests ... OK`.
- Whole suite: `Ran 91 tests ... FAILED (errors=2)`. These are the same 2 expected errors as before: QA's TASK-001 `test_risk_*` tests record the behaviour that TASK-001 attempt 2 removed. They're QA-owned, and I didn't change them. Nothing in TASK-006 fails.

## Known limits

- With the file-backed store (TASK-002), analyses already saved in `data/registry.json` keep the old text until that repository is rescanned. AC5 asks for this ("not automatically changed"). The in-memory seed analyses are rebuilt at start-up, so they show the new text.

## Attempts

- Attempt 1: first version.
