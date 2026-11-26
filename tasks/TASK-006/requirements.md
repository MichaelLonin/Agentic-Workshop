# Requirements: TASK-006

## The request in one sentence

Correct the singular wording in repository analysis summaries when there is one open finding.

## Acceptance criteria

- **AC1:** Given a newly generated analysis with one open finding, its summary says `1 open finding.`
- **AC2:** Given a newly generated analysis with zero open findings, its summary says `0 open findings.`
- **AC3:** Given a newly generated analysis with more than one open finding, its summary uses the count followed by `open findings.`
- **AC4:** The finding count and the rest of the analysis and summary remain unchanged by this wording correction.
- **AC5:** Both an initial analysis and a rescan use the correct wording; existing stored analyses are not automatically changed or rescanned.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- Delegated Product Owner decision: Apply the singular only to a count of one, keeping all other counts plural, as the report says the other numbers read fine.
- Delegated Product Owner decision: Preserve stored analyses and existing restart behavior; corrected wording appears when an analysis is generated or regenerated.

## Out of scope

- Changes to finding counts, other analysis content, storage, or restart behavior.

## Product Owner decision

Pending acceptance.
