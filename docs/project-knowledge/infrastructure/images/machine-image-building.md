---
title: Machine image building
aliases: ["Machine image building"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure]
related_code:
  - "../../../../infra/images/scripts/"
  - "../../../../infra/images/packer/"
  - "../../../../infra/tests/images/"
related_docs:
  - "Machine images"
  - "Packer implementation"
---

# Machine image building

Use this workflow when a reusable host image must change. It is separate from
application deployment: Packer creates image artifacts, while Terraform and
CDK consume completed identifiers.

```text
prepare source --> validate configuration --> build --> verify artifact
                                                         |
                            +----------------------------+----------------+
                            |                                             |
                       Proxmox template                           AWS AMI publication
                            |                                             |
                     Terraform consumes                           CDK/hosts consume
```

## Proxmox lineage

Create local ignored configuration from the provided examples, then run the
dispatcher from the repository root:

```sh
infra/images/scripts/image prepare proxmox
infra/images/scripts/image prepare proxmox --apply
infra/images/scripts/image build proxmox all
```

The first `prepare` is a preflight. `--apply` creates a missing source template;
replacing a mismatched source requires `--apply --replace`. The aggregate build
runs the golden, LocalStack fixture, and PostgreSQL fixture targets in that
order, then verifies the Proxmox source/template disk policy. Individual
targets are `golden`, `localstack`, and `db`; `--validate-only` validates their
Packer configuration without building images.

The configured Proxmox build targets share a reserved build address, so their
builds are sequential. The standard lineage is source template 8999, golden
template 9000, LocalStack fixture 9001, and PostgreSQL fixture 9002. The image
workflow does not deploy rehearsal VMs.

## AWS AMI

Copy the AWS Packer variable example, authenticate the selected AWS profile,
then run:

```sh
infra/images/scripts/image doctor aws
infra/images/scripts/image build aws
infra/images/scripts/image publish aws --environment staging --dry-run
```

An AWS build restricts Packer's temporary SSH security group to the build
workstation's detected public address, derives the `source_commit` tag from
Git, and verifies its AMI and snapshot before it completes. When the selected
AWS CLI profile uses a login session, the dispatcher supplies Packer with a
refreshable credential-process bridge without persisting credentials.
The golden image carries the deployment bootstrap scripts, shared Compose
definitions, their referenced Alloy and Squid service configuration, and the
AWS strategy overrides. Image verification fails if any of those runtime
assets are absent.
Publication accepts only `dev`, `staging`, or `prod`, checks that the caller
account matches the CDK configuration, verifies the AMI again, and writes the
AMI ID to the environment's configured SSM parameter. `--dry-run` performs the
prechecks without the SSM write. Publication does not run CDK deployment.

When an AWS builder repeatedly stops at `Waiting for SSH`, rerun the build in
diagnostic mode:

```sh
infra/images/scripts/image build aws --diagnose-ssh
```

This retains normal Packer cleanup while recording the live builder identity,
EC2 status checks, boot console, temporary security-group rules, subnet
routing, network ACL, workstation public address, repeated TCP/22 probes, and
Packer's internal log in permission-restricted files under `/tmp`. Review the
reported paths before retrying or changing the connection design.

## Validation boundary

```sh
infra/tests/images/validate.sh
```

The repository suite checks the image scripts and Packer definitions. Live
Packer builds, Proxmox inspection, AWS access, and publication remain explicit
operator actions.

## Related documents

- [[images-index|Machine images]]
- [[packer|Packer implementation]]
