---
title: Deployment documentation
aliases: ["Deployment documentation"]
document_type: overview
status: verified
authority: canonical
verified_against_commit: 0edae9082dc3381cc1376e8a81276bf5c7bebf88
tags: [infrastructure, ci-cd]
related_code:
  - "../../../../infra/deployment/"
  - "../../../../.github/workflows/"
related_docs: ["Infrastructure knowledge", "Deployment model", "Cloud deployment"]
---

# Deployment documentation

Owns the checked-in deployment topology and the bounded AWS publication
workflows. These documents describe infrastructure definitions and automation
in the repository; they do not attest that any stack is deployed or healthy.

## Documents in this branch

- [[deployment-model|Deployment model]] describes the environment shapes and
  CDK deployment boundary.
- [[cloud-deployment|Cloud deployment]] describes the staging frontend and
  runtime-image publication workflows.

## Boundary

Host bootstrap and container definitions are implemented under `infra/`, but a
checked-in definition is not evidence of a live release. The current AWS
workflows publish frontend assets and runtime images; they do not apply CDK,
promote an image into runtime parameters, run migrations, or restart hosts.
