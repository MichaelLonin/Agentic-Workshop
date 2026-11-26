# Requirements: TASK-008

## The request in one sentence

Let people optionally list their repositories with the most recently scanned first, while keeping the normal order unchanged.

## Acceptance criteria

- **AC1:** Given a caller does not request recent-scan ordering, when they list repositories, then their repositories are returned in the existing ascending repository ID order with the existing response fields.
- **AC2:** Given a caller requests recent-scan ordering, when their repositories have different latest scan times, then the list is ordered from most recently scanned to least recently scanned and contains the same repository summary fields as the normal list.
- **AC3:** Given repositories have the same latest scan time, when recent-scan ordering is requested, then those repositories appear in ascending repository ID order; repositories with no scan time appear after those with a scan time, also in ascending ID order.
- **AC4:** Given a successful registration, individual scan, or bulk scan, when the caller next requests recent-scan ordering, then the order reflects the latest recorded scan times. A failed scan does not change the ordering based on scan times.
- **AC5:** Given either ordering is requested, when a caller lists repositories, then only their own repositories appear; a caller with no repositories receives an empty list and an unknown user receives the existing unauthorized response.
- **AC6:** Given a list request in either order, when it completes or the app restarts normally, then listing has not changed repository or scan data, and the existing storage and restart behavior remains unchanged.

## Assumptions

- None.

## Open questions

- None.

## Decisions

- **Delegated Product Owner decision:** Recent-scan ordering is opt-in for each list request; the existing order remains the default. The Architect can specify how callers select it for the API.
- **Delegated Product Owner decision:** Use the existing latest scan time, including the scan performed at registration; ties use ascending ID and missing scan times go last, so results are predictable.
- **Delegated Product Owner decision:** Keep the existing list fields, access rules, and storage/restart behavior; this request changes ordering only.

## Out of scope

- Changing scan behavior, repository data, or the ordering of other responses.

## Product Owner decision

Pending acceptance.
