# CDK prerequisites

CDK operations cross local tooling, AWS account authority, repository policy,
external providers, and runtime configuration. Satisfy the relevant boundary
before treating a failed synth or deploy as an implementation defect.

## Local tooling

Use the package setup in the [package README](../README.md). The Python and Node
dependency locks own tool versions; avoid global substitutions when the
repository-pinned command is available.

## AWS authority

Local preview and deployment require an authenticated identity for the target
account and region. Routine automation should use short-lived role assumption.
Account bootstrap is a separate, broader authority and should not become a
runtime credential.

The CDK toolkit must already be bootstrapped for an account and region before
its first deployment. This is account foundation, not application runtime.

## External contracts

FlowForm relies on external identity, naming, email-delivery, source-control,
and approval boundaries. Some are imported foundations, some are configured
providers, and some require human authorization. Confirm the target
environment's contracts rather than assuming another environment's settings
are interchangeable.

The conceptual ownership model lives in
[External platform boundaries](../../../../../docs/project-knowledge/infrastructure/external-platform-boundaries.md).

## Runtime inputs

A deploy may require already published machine images, promoted container
releases, non-secret runtime configuration, and seeded secret values. Those
inputs have separate owners and lifecycles. CDK declares how an environment
refers to them; it does not build every artifact or generate every confidential
value during deployment.

Use the [AWS operations index](../../operations/README.md) to locate the owning
artifact, configuration, stack, or host workflow.

## Before a live change

- Confirm the intended environment and authenticated account.
- Inspect the diff and understand destructive or replacement effects.
- Confirm required artifacts and externally supplied inputs exist.
- Identify the rollback and retained-state boundary.
- Know what live verification will demonstrate after deployment.

Exact provider console procedures and sensitive identifiers should not be
copied into this page. Keep them with the controlled operator system that owns
them.
