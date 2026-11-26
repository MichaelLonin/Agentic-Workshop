# Requirements: TASK-002

## The request in one sentence

Allow an owner to remove a registered repository and its analysis from the registry.

## Acceptance criteria

- **AC1:** Given a known user and a repository they own, when they request its removal, then the request succeeds and the repository no longer appears in their repository list.
- **AC2:** After successful removal, fetching the repository or its analysis and requesting a new scan for its former ID all report that the repository does not exist; its stored analysis is also removed.
- **AC3:** After successful removal, the repository and its analysis remain absent after an ordinary application restart; an explicit reset of demo data may restore seed data.
- **AC4:** When a known user requests removal of another user's repository, the request is denied and that repository and its analysis remain unchanged.
- **AC5:** When an unknown user requests removal, the request is denied; when a known user requests removal of an absent repository, they are told it does not exist. Neither request changes other data.
- **AC6:** If removal cannot complete, the user is told it failed and the repository and analysis remain available and unchanged. Removing one repository does not change any other repository or its analysis.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- **Delegated Product Owner:** Removal applies to the registry and its analysis, not the actual source repository hosted elsewhere; this addresses mistaken registrations without deleting source code.
- **Delegated Product Owner:** Removal is immediate on request, with no separate confirmation or undo; an absent ID reports not found. This keeps the API interaction simple.
- **Delegated Product Owner:** A successful removal survives an ordinary restart; explicitly resetting demo data may restore seed records. This makes “once removed” meaningful while preserving an intentional reset.
- **Delegated Product Owner:** A failed removal leaves both the record and its analysis unchanged so users are not left with a partial result.

## Out of scope

- Deleting or changing the source repository on its hosting service.

## Product Owner decision

- Pending acceptance after QA.
