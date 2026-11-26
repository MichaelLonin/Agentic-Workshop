# Requirements: TASK-007

## The request in one sentence

Let a user scan all of their registered repositories in one action before the weekly review.

## Acceptance criteria

- **AC1:** Given a known user with one or more registered repositories, when they request a bulk scan, then every repository they own is scanned once and the response identifies each repository and its new analysis.
- **AC2:** After a successful bulk scan, each owned repository's latest analysis and last-scanned time reflect that scan; repositories and analyses owned by other users are unchanged and are not returned.
- **AC3:** Given a known user with no registered repositories, a bulk scan succeeds with an empty result and changes nothing.
- **AC4:** An unknown user cannot run a bulk scan or receive repository results; no repository or analysis changes.
- **AC5:** If scanning or saving any repository in the bulk action fails, the action reports failure and none of the repositories or analyses are changed. Successful scan results retain the app's existing persistence and restart behavior.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- **Delegated Product Owner:** Scan all repositories currently registered to the caller, including one or zero, using the existing single-repository analysis behavior; return the new results together so the user can review them.
- **Delegated Product Owner:** Treat the bulk action as all-or-nothing and report failure if any scan or save fails, so the user is not left with a misleading partial review.

## Out of scope

- Scheduling scans, changing repository ownership, or changing the existing storage and restart behavior.

## Product Owner decision

- Pending acceptance after QA.
