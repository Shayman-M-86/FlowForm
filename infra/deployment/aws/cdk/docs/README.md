# CDK operator and maintenance index

This directory contains only guidance needed to operate or maintain the CDK
package. It is deliberately not a second architecture library.

## How to run this area

| Need | Owner |
| --- | --- |
| Set up and validate the CDK package | [Package README](../README.md) |
| Understand prerequisites and authority boundaries | [Prerequisites](prerequisites.md) |
| Preview or deploy an AWS stack | [Deployment](deployment.md) |
| Publish the current frontends manually | [Frontend deploy](runbooks/frontend-deploy.md) |
| Deliberately remove an environment | [Teardown](runbooks/teardown.md) |
| Build or publish machine images, promote containers, or converge hosts | [AWS operations](../../operations/README.md) |

Command help from the owning script is authoritative when it disagrees with a
Markdown example.

## Documentation ownership

Keep a document here only when an operator needs it while running or changing
this package. Appropriate subjects are prerequisites, validation, deployment,
teardown, and package-specific maintenance rules.

Route other material by purpose:

- Durable architecture, trust, lifecycle, and recovery concepts belong in
  Project Knowledge.
- A choice and its rationale belong in Development Workspace decisions.
- Active sequencing, experiments, and investigations belong in their matching
  Development Workspace areas.
- Completed or superseded sketches belong in the archive.
- Generated resource inventories and descriptions of source layout should be
  deleted; the implementation and synthesized output already own those facts.

Do not create new local documents that enumerate stack classes, settings,
parameters, account identifiers, hostnames, or temporary implementation phases.
Those details drift quickly and are easier to discover from their owner.

## Maintenance checklist

When CDK behaviour changes:

1. Update source and synth-time assertions together.
2. Run the package validation commands from the package README.
3. Review the operator guides only if invocation, prerequisites, destructive
   effects, or recovery behaviour changed.
4. Review Project Knowledge when the architecture, trust boundary, ownership,
   or lifecycle meaning changed.
5. Put unsettled ideas into Development Workspace rather than presenting them
   here as current behaviour.

The main conceptual owners are
[Deployment architecture](../../../../../docs/project-knowledge/infrastructure/deployment/deployment-index.md),
[Deployment design forces](../../../../../docs/project-knowledge/infrastructure/deployment/design-forces-and-evolution.md),
[External platform boundaries](../../../../../docs/project-knowledge/infrastructure/external-platform-boundaries.md),
[Runtime infrastructure security](../../../../../docs/project-knowledge/security/runtime-infrastructure-security.md),
and [Release recovery and readiness](../../../../../docs/project-knowledge/operations/release-recovery-and-readiness.md).
