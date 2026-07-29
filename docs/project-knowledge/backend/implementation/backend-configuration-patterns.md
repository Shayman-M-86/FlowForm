---
title: Backend configuration patterns
aliases: ["Backend configuration patterns"]
document_type: implementation
status: verified
authority: canonical
verified_evidence_digest: sha256:31061852b3fdb13ae9486f6d432b8e3386e46336047580d7fe235750d818efa5
last_edited: 2026-07-29
tags: [backend, configuration]
related_code:
  - "../../../../backend/app/core/config.py"
  - "../../../../backend/app/core/factory.py"
  - "../../../../backend/app/aws/startup_validation.py"
  - "../../../../infra/env/"
  - "../../../../scripts/secrets/"
related_docs:
  - "Backend implementation documentation"
  - "Configuration implementation"
  - "Secrets and configuration"
---

# Backend configuration patterns

This draft records the configuration boundary centred on
`backend/app/core/config.py`. A runtime setting should enter through the typed
settings model and be supplied to the application assembly path, rather than
being read from the environment at a route or service call site.

```text
environment / secret file
           |
           v
     typed settings
           |
     startup validation
           |
           v
  application factory
           |
 extensions / services / clients
```

The legacy implementation guide describes nested environment configuration,
typed validation, secret-file support, and startup validation for selected
external dependencies. Group a new value with the responsibility that owns it;
validate incompatible settings during configuration construction; then pass the
typed value through the factory/extension boundary. Secrets need a delivery
mechanism appropriate to their sensitivity rather than a tracked plaintext
environment file.

Exact setting names and provider checks require re-verification against the
linked code and configuration references before this document can be promoted.

## Related documents

- [[implementation-index|Backend implementation documentation]]
- [[configuration|Configuration implementation]]
- [[secrets-and-configuration|Secrets and configuration]]
