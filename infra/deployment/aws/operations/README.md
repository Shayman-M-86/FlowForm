# AWS operations

This directory contains the operator-facing boundaries for AWS deployment
work. The scripts are intentionally thin: they validate the requested
operation and then call the existing Packer, image, CDK, ECR, SSM, or host
implementation. They are suitable for a developer workstation or a CI
workflow and do not replace the implementation they invoke.

## `machine-images/`

Operations for the Base, App, and Proxy AMIs.

| Script | Purpose |
| --- | --- |
| `doctor.sh` | Check the local AWS image-building prerequisites and credentials. |
| `build.sh` | Build Base, App, Proxy, or the complete three-level AMI lineage. Live builds require a clean worktree unless explicitly overridden. |
| `verify.sh` | Verify a built AMI, its storage policy, tags, and parent lineage. |
| `artifact.sh` | Print the AMI ID recorded by the latest Packer manifest. |
| `publish.sh` | Publish a verified App or Proxy AMI ID to its environment SSM parameter. |
| `prune.sh` | Preview or remove old, unprotected FlowForm AMIs and their snapshots. |

## `container-releases/`

Operations for immutable Backend, Caddy, Squid, and Alloy releases.

| Script | Purpose |
| --- | --- |
| `publish-staging.sh` | Validate the image-source contract or publish all staging images for one exact commit. |
| `promote.sh` | Promote a published digest manifest into the complete App and Proxy release parameters. |

Publishing creates ECR artifacts. Promotion selects which artifacts an
environment should run. Neither operation automatically restarts a host.

## `stacks/`

Operations that cross the CDK and CloudFormation boundary.

| Script | Purpose |
| --- | --- |
| `deploy.sh` | Diff and deploy an exact FlowForm stack, with optional exclusive deployment. |
| `deploy-application.sh` | Diff and deploy only the environment Application stack, forcing CloudFormation to re-resolve the App and Proxy AMI parameters. |

## `hosts/`

Operations against already deployed EC2 hosts.

| Script | Purpose |
| --- | --- |
| `converge-role.sh` | Restart the baked App or Proxy role service through SSM so it reloads release and runtime configuration without replacing EC2. |
| `replace-role.sh` | Reserved for independent role-host replacement. It currently exits with a TODO because both hosts belong to one Application stack. |

Host convergence requires the target instance to be registered and online in
Systems Manager, plus caller permission to send and inspect commands.
The Proxy role currently has the managed-instance policy; the App role still
needs its SSM channel permissions completed before remote App convergence is
available.

## `configuration/`

Operations that change environment-specific runtime values.

| Script | Purpose |
| --- | --- |
| `update-role.sh` | Reserved for a schema-aware configuration updater. It currently exits with a TODO instead of performing arbitrary SSM writes. |

Until that updater exists, CDK-owned configuration is changed through CDK,
container releases are changed through promotion, and `hosts/converge-role.sh`
applies the selected values to a running host.

## `_lib/`

Shared path discovery and argument validation used by the operation scripts.
It is an internal implementation detail and is not run directly.
