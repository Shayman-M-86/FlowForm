---
title: Three-level AMI reorganization checkpoint
aliases: ["Three-level AMI reorganization checkpoint"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, configuration, ci-cd]
related_code:
  - "../../../infra/contracts/"
  - "../../../infra/containers/"
  - "../../../infra/machine-images/"
  - "../../../infra/deployment/aws/cdk/"
related_docs:
  - "Engineering planning"
  - "AWS staging runtime convergence"
  - "AWS stack specifications"
---

# Three-level AMI reorganization checkpoint

> Paused implementation checkpoint. This page records an unfinished working
> tree; it is not a description of deployed infrastructure or a deployment run
> sheet.

## Objective

Reorganize the AWS infrastructure around three machine-image release units:

```text
Base AMI
├── App AMI
└── Proxy AMI
```

Container releases remain independent of host releases. The base image owns
shared host capability, role images own app- or proxy-host orchestration, and
containers own the software and configuration of their individual services.

## Stop point

The implementation was deliberately paused before integration and cutover.
Nothing from this reorganization has been committed, published, or deployed.

| Area | State at pause | Important qualification |
| --- | --- | --- |
| Container ownership | Substantially implemented | Focused Caddy, Squid, Alloy, shell, and container checks passed before the remaining machine-image edits; the final integrated invariant suite has not been rerun |
| Shared contracts | Draft implementation exists | Canonical instance, release, runtime-host, runtime-parameter, and image-source contracts now live under `infra/contracts/`; their final shape is not accepted yet |
| Machine-image layout | Partially implemented | The old `infra/images/` tree has been moved and split into base, app, proxy, shared, and Packer areas; the complete build, verification, publication, pruning, and lineage workflow has not been proven |
| App and Proxy AMIs | Draft build and host assets exist | Role build files, Compose files, services, and bootstrap helpers exist, but Packer validation and built-image inspection have not been completed |
| AWS CDK | Partially implemented | Separate app and proxy AMI parameters and minimal instance-context wiring have been started; the CDK test suite and synthesis have not been completed |
| Proxmox and rehearsal compatibility | Not completed | Existing Terraform, cloud-init, and rehearsal paths still refer to moved files and are expected to be broken until adapters or new ownership are agreed |
| Publication automation | Partially updated | One staging image workflow uses the new image-source contract, but the publisher script and other path consumers still require review |
| Documentation | Checkpoint only | Existing current-state and runbook documents have not been rewritten because the target structure is still under review |

## Provisional structure now present

```text
infra/
├── contracts/
├── machine-images/
│   ├── packer/
│   ├── shared/
│   ├── base/
│   ├── app/
│   ├── proxy/
│   └── scripts/
├── containers/
│   ├── backend/
│   ├── caddy/
│   ├── squid/
│   ├── alloy/
│   └── strategies/
└── deployment/
    ├── aws/
    └── proxmox/
```

The working tree represents real moves plus new files, not a completed
behavior-preserving migration. Deleted old paths and untracked new paths must
remain together when reviewing or checkpointing the work.

## Decisions currently encoded but open for review

The partial implementation assumes:

- `infra/machine-images/` is the permanent replacement for `infra/images/`;
- generic App and Proxy Compose topology belongs with each role AMI;
- Caddy, Squid, Alloy, and Backend own their service configuration inside
  first-class container build contexts;
- shared runtime and release schemas belong in `infra/contracts/`;
- `/etc/flowform/instance-context.json` is the host/CDK hand-off;
- `flowform-app.service` and `flowform-proxy.service` are the host entry points;
- staging publishes separate `/flowform/staging/ec2/appAmiId` and
  `/flowform/staging/ec2/proxyAmiId` parameters;
- the existing CDK stack boundaries remain intact during the first cutover;
- the old runtime-parameter path may temporarily be a compatibility link to the
  canonical contract.

These are implementation choices, not yet durable architecture decisions.

## Concerns to settle before resuming

1. Should role Compose topology live under `machine-images/app` and
   `machine-images/proxy`, or under a separate host-runtime area?
2. Is `machine-images` the right ownership name and boundary?
3. Is a top-level `infra/contracts` area useful, and are compatibility links
   acceptable?
4. Should Proxmox consume the same role-host assets, keep separate assets, or
   be explicitly deferred from this migration?
5. Are the instance-context fields, filesystem path, service names, and
   bootstrap command boundaries appropriate?
6. Should release-manifest promotion be implemented in this migration or
   deferred until the three AMIs work?
7. Should one CDK Application stack continue to own both EC2 roles during the
   first cutover?
8. Should old paths receive temporary adapters, or should this be an explicit
   one-time breaking repository migration?

## Work remaining after those decisions

1. Adjust the directory and ownership model to the accepted shape.
2. Finish the base, App, and Proxy Packer builds and prove exact parent lineage.
3. Finish the image command's role-aware build, verify, publish, and prune
   behavior.
4. Finish and test the CDK role-AMI and instance-context integration.
5. Repair or deliberately redesign Proxmox and rehearsal path consumers.
6. Update all publisher scripts, workflows, tests, and remaining old-path
   references.
7. Run the focused container, image, CDK, Terraform, and documentation checks.
8. Only then build and publish role AMIs or attempt a staging cutover.

## Safe resume checklist

Start by reviewing the working tree rather than rerunning the migration:

```bash
git status --short
git diff --stat
rg -n 'infra/images|infra/deployment/bootstrap|containers/runtime|strategies/aws' \
  infra .github docs
```

After the structural decisions are resolved, the minimum integration checks
should cover:

```text
container invariant and configuration validation
machine-image structural validation
Packer formatting and validation for base, App, and Proxy
role-asset isolation and AMI lineage
shell syntax and focused ShellCheck
CDK formatting, type checks, assertions, and synthesis
Proxmox Terraform formatting, validation, and template path checks
documentation authoring validation and impact review
```

Do not deploy, publish AMI parameters, prune old images, or remove the existing
deployment path from this checkpoint state.
