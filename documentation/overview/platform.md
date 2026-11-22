---
description: Product responsibilities and navigation to source repositories.
---
# Platform and repositories

**Status: Current, high-level.**

FlowForm supports survey authoring, conditional question flows, publishing immutable survey versions, participant access, submission and response review. Projects group surveys and collaborative work.

The source repository is [FlowForm](https://github.com/Shayman-M-86/FlowForm). Its [engineering tour](https://github.com/Shayman-M-86/FlowForm/blob/main/ENGINEERING_TOUR.md) and application code provide implementation details. Documentation here describes boundaries that span code directories and environments.

## Product surfaces

**Studio** provides project management, survey building, publishing, participation management and response review.

**Participant application** renders published survey versions, evaluates conditional presentation and submits answers.

**Backend** implements domain operations, authentication integration, authorization and data persistence.

**Infrastructure** delivers static assets and API services, databases, edge access and operational tooling.

See [System overview](../architecture/system-overview.md).
