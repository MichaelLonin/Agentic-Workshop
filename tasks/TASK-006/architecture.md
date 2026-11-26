# Architecture: TASK-006

<!-- Owner: ARCHITECT. Security notes: SECURITY. A few bullets, not a design document. -->

## Approach

- The summary text is built in one place: `analyze()` in `app/analyzer.py`, `f"{files} files, mostly {main_language}. {open_findings} open findings."`.
- Add a small pure helper, `findings_text(count)`, which returns `"1 open finding"` when `count == 1` and `f"{count} open findings"` otherwise (0 and 2–11 stay plural). Use it in the summary line, followed by `"."` as today (AC1–AC3).
- Don't change anything else in `analyze()`: the numbers, the field names and the rest of the summary text stay the same, so the same URL gives the same analysis apart from that one word (AC4).
- Registration and `scan` already call `analyze()`, so both pick up the new wording with no other change. Stored analyses aren't touched or migrated (AC5).

## Parts that change

- `app/analyzer.py`: `findings_text()` and the summary line.
- `tests/`: unit tests on `findings_text(0)`, `(1)`, `(2)` and `(11)`, plus one test showing that `analyze()`'s summary ends with `findings_text(result["open_findings"]) + "."`. Using the helper means the tests don't depend on finding a URL whose hash happens to give exactly 1 finding.
- Not changed: `app/service.py`, `app/server.py`, `app/store.py`, `docs/api.md` (the API shape is the same).

## Interface

- No API change. `GET /repositories/{id}/analysis` and `POST /repositories/{id}/scan` return the same fields. Only `summary` reads `... 1 open finding.` when `open_findings` is 1.

## Risks and limits

- **When old summaries change:** the in-memory store rebuilds the seed analyses at start-up, so they show the new wording after a restart, because they are "newly generated" there. With the file-backed store from TASK-002, analyses already saved in `data/registry.json` keep the old text until that repository is rescanned. This is what AC5 asks for ("not automatically changed").
- `files` is always at least 40 (`40 + digest[2] * 3`), so "1 files" can't happen and needs no fix.

## Security notes

- None reported.
