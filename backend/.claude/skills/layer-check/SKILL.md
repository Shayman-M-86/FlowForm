---
name: layer-check
description: Remind Claude of FlowForm's strict backend layer rules before editing Python files
user-invocable: false
paths: ["backend/**/*.py"]
---

Before editing any backend Python file, verify the edit respects the layer contract:

- Routes: HTTP parsing only — no SQL, no session management, no business logic
- Services: Only layer that coordinates both DBs
- Repositories: One DB only, named query methods, no workflow logic
- ORM models: Pure persistence — no business logic, no cross-DB relationships
- Response DB: Never receives real user_id

If the proposed change would violate a layer boundary, flag it before proceeding.
