# TASK-005

<!-- Added by a facilitator. Nobody edits this file; a facilitator may add a "Follow-up from Business" below. -->

## Request from Business

Bug report from Operations: our monitoring tool checks GET /health every minute, and it always sends a small body with the request. The API answers 400 "Body is not valid JSON", so the monitor thinks the app is down. A GET request shouldn't care about a body.
