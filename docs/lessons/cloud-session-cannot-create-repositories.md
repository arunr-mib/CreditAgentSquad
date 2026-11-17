A cloud session cannot create a GitHub repository; the owner must create it, then it can be attached.

Confirmed 2026-11-17: `gh repo create` and `POST /user/repos` both return 403 "sessions are bound to their configured repositories". GraphQL is also unavailable; use REST paths under `repos/{owner}/{repo}`.

Rule: ask the owner to create an empty repository, then attach it with push access and push. Do not retry creation.
