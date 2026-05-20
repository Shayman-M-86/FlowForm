---
name: layer-check
description: Use before editing FlowForm backend Python files to verify changes respect the backend layer contract.
---

Before editing any backend Python file, verify the edit respects the layer contract:

- Routes: HTTP parsing only; no SQL, no session management, no business logic.
- Services: only layer that coordinates both DBs.
- Repositories: one DB only, named query methods, no workflow logic.
- ORM models: pure persistence; no business logic, no cross-DB relationships.
- Response DB: never receives real `user_id`.

If the proposed change would violate a layer boundary, flag it before proceeding.
