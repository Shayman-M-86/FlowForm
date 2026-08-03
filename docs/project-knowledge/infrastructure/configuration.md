---
title: Configuration and secrets
aliases: ["Configuration and secrets", "Configuration implementation", "Secrets and configuration"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [configuration, infrastructure, security]
related_code:
  - "../../../backend/app/core/config.py"
  - "../../../backend/app/db/iam_auth.py"
  - "../../../infra/contracts/runtime-parameters.json"
change_triggers:
  - "../../../infra/deployment/bootstrap/"
  - "../../../scripts/secrets/"
related_docs: ["Infrastructure knowledge", "Local infrastructure", "Deployment architecture", "External platform boundaries"]
---

# Configuration and secrets

The backend owns the typed configuration model. Deployment and local tooling
provide values in the form that model accepts; they do not redefine application
settings. Non-secret runtime identity is represented by infrastructure
contracts, while confidential values are delivered at runtime rather than
embedded in source, image builds, or deployment declarations.

```text
environment inputs + file-backed secrets
                 |
                 v
        typed application settings
                 |
                 v
        application and runtime services
```

## Boundaries

Configuration names, roles, and release information belong to
`infra/contracts/`. Bootstrap and local tooling consume those contracts and
materialise only the values required by the selected environment. The backend
can use either password-backed or identity-backed database authentication; the
chosen mode is explicit configuration, not an implication of environment name.

Secrets must remain outside committed configuration and build contexts. Runtime
consumers receive them through restricted file-backed paths where required.
Local development has its own ignored inputs and persistent database state;
replacing its credentials may require an intentional data reset. Exact setup
and recovery procedures belong with the scripts that implement them.

Some required inputs originate outside FlowForm's deployment authority. Their
ownership, bootstrap authority, recovery expectation, and live verification
belong to [[external-platform-boundaries|External platform boundaries]]. This
keeps the application configuration contract separate from registrar,
provider, account, approval, and source-control administration.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[local-infrastructure|Local infrastructure]]
- [[deployment-index|Deployment architecture]]
- [[external-platform-boundaries|External platform boundaries]]
