# Requirements: TASK-003

## The request in one sentence

Let repository owners update outdated descriptions of their own repositories.

## Acceptance criteria

- **AC1:** Given an existing repository owned by the caller, when the caller supplies a valid replacement description, then the update succeeds and the repository detail shows that description on a subsequent read.
- **AC2:** A description may be a string, including an empty string, or null to clear it, consistent with registration. A missing description, a non-string non-null description, or an invalid request is rejected without changing the repository.
- **AC3:** An unknown user cannot update a description (401); a known non-owner cannot update another user's repository (403); and an unknown repository returns 404. No rejected request changes data.
- **AC4:** Updating a description changes no other fields of that repository or data belonging to other repositories and does not run or change its analysis.
- **AC5:** The update follows existing storage behavior: in-memory changes last for the life of that store; file-backed changes survive restart. If saving fails, the caller receives an error and the previous data remains unchanged.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- **Delegated Product Owner decision:** Accept strings (including empty strings) and null for descriptions, matching existing registration; require the description to be explicitly supplied so accidental omissions cannot clear it.
- **Delegated Product Owner decision:** Keep existing ownership, error and storage behavior, so the feature fits the current registry without changing its other behavior.

## Out of scope

- Editing other repository fields or changing ownership, analysis, or storage and restart behavior.

## Product Owner decision

- Pending acceptance after QA.
