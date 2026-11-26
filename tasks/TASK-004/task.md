# TASK-004

<!-- Added by a facilitator. Nobody edits this file; a facilitator may add a "Follow-up from Business" below. -->

## Request from Business

Bug report from the integration team: when our client calls an endpoint with the wrong method, the API answers 405, which is right. But the response has no Allow header, so our client library can't tell us which method to use, and it crashes. Please add the header.
