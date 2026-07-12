# Target 01: Runtime Inventory

Goal: map current route -> service -> repository flow before changing contracts.

Open only these shared files first:

* `../agent-operating-rules.md`
* `../pass-template.md`

Relevant policy docs:

* `../../core-policies.md`
* current flow docs only if inventory exposes a specific route

Likely code files:

* `backend/app/api/v1/public.py`
* `backend/app/services/public_submissions/api/session_management.py`
* `backend/app/services/public_submissions/api/survey_resolve.py`
* `backend/app/services/public_submissions/core/access_resolver.py`
* `backend/app/services/public_submissions/core/subject_resolver.py`
* `backend/app/services/public_submissions/core/subject_token.py`
* `backend/app/services/public_submissions/core/session_starter.py`
* direct repository helpers called by those services

Expected output:

* compact route -> service -> repo map
* hidden consumers or stale old-service consumers
* first contract that should change

Do not edit behavior in this pass unless user explicitly asks.
