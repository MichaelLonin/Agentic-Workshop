# Requirements: TASK-001

## The request in one sentence

Let a user register a repository by name and URL, optionally add a description, and immediately receive an analysis for their own repository.

## Acceptance criteria

- **AC1:** Given a known user supplies a nonblank name and a valid HTTP or HTTPS URL with a host, when they register a repository, then it is created with those values and belongs to that user.
- **AC2:** Given a user supplies a description during registration, when they retrieve the new repository, then its description is present; registration also succeeds without a description.
- **AC3:** Given a registration request has a missing or blank name, a missing URL, or a URL that is not an absolute HTTP or HTTPS URL with a host, when it is submitted, then it is rejected and no repository is created.
- **AC4:** Given a successful registration, when the owner lists their repositories or retrieves the new repository, then it is available to them; another user cannot retrieve it under the existing ownership rules.
- **AC5:** Given a successful registration, when the owner immediately requests its analysis, then an analysis for the new repository is available without a separate scan.
- **AC6:** Given a repository URL is already registered by any user, when anyone tries to register the same URL again, then the request is rejected and no additional repository is created. Compare URLs after removing leading and trailing whitespace; otherwise compare the text exactly.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- **Product Owner (delegated):** Reject duplicate URLs across all users; use exact text after trimming surrounding whitespace, so the rule is testable.
- **Product Owner (delegated):** Accept any absolute HTTP or HTTPS URL with a host; do not restrict registration to a list of Git hosts. This accommodates private and less common hosts.

## Out of scope

- Changes to the existing simulated analysis or the app's in-memory persistence model.

## Product Owner decision

- Pending implementation and QA.
