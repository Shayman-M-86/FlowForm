---
title: Machine image building
aliases:
  - "Machine image building"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [infrastructure]
related_code:
  - "../../infra/images/packer/"
  - "../../infra/images/scripts/"
  - "../../infra/images/packer/provisioners/"
  - "../../infra/tests/images/"
related_docs:
  - "Cloud deployment"
  - "Packer implementation"
  - "Deployment model"
  - "Proxmox rehearsal implementation"
  - "Infrastructure resources"
---

# Machine image building
Describes the Packer workflow for AWS and Proxmox Amazon Linux 2023 golden
images and the Proxmox-only LocalStack and PostgreSQL fixtures. The platforms share
provisioning but deliberately use different official base images and disks.
It covers image construction only; [[deployment-model|Terraform deployment]]
clones a completed Proxmox template and does not invoke Packer.

## Trigger
Run this workflow when the reusable operating-system image needs changing: for
example, an updated Amazon Linux source image, common package change, or image
hardening change. It is not a normal application or environment deployment
step.

## Preconditions
- Packer and its configured Proxmox plugin are available on the Linux/WSL build
  host.
- `infra/images/config/proxmox-source.env` exists and identifies the Proxmox SSH host,
  pinned AL2023 KVM source, storage, source-template VMID, bridge, native disk
  policy, and maximum virtual disk size.
- `infra/images/packer/variables/proxmox.auto.pkrvars.hcl` exists with Proxmox API
  credentials, node, source-template name, output VMID, and a reserved build
  address.
- The reserved build address must not respond to ping; the Packer wrapper
  rejects a build if it does.

## Ordered steps
1. Run `infra/images/scripts/image prepare proxmox` for a
   non-mutating preflight, then rerun with `--apply` when the pinned source
   template needs creation or replacement. It imports the official AL2023 KVM
   qcow2 and produces source template `8999` in the current local rehearsal.
   Use `--apply --replace` to rebuild an older oversized template; do not shrink
   its XFS disk in place.
2. Run `infra/images/scripts/image build proxmox golden`. It
   initializes Packer plugins, validates the configuration, and runs only the
   Proxmox clone builder.
3. Packer clones the source template, applies shared and Proxmox-specific build
   steps, cleans image identity state, and converts the result to template
   `9000` in the current local rehearsal.
4. Run `infra/images/scripts/image build proxmox localstack`. Packer clones
   golden template `9000`, extracts the exact image references from the three
   maintained rehearsal Compose files, and preloads them into fixture `9001`.
5. Run `infra/images/scripts/image build proxmox db`. Packer independently
   clones golden template `9000` and preloads only the image declared by the
   rehearsal DB Compose file into fixture `9002`.
6. Run Terraform separately. Proxy and app clone the golden template, while
   LocalStack and PostgreSQL clone their respective fixture templates.

For AWS, copy `variables/aws.auto.pkrvars.hcl.example`, authenticate the AWS
CLI, and run `infra/images/scripts/image build aws`. The builder selects the
Amazon-owned minimal AL2023 EC2 AMI with kernel 6.1 and creates a 10 GiB
encrypted gp3 root. It never imports the Proxmox QCOW2. After Packer completes,
the dispatcher verifies the resulting AMI and snapshot size, encryption, volume
type, and absence of additional EBS mappings before the AMI may be published.
`image publish aws --environment <dev|staging|prod>` then derives the SSM
parameter and region from the CDK environment configuration, verifies the AMI
again, and publishes the ID for CDK to consume. Use `--dry-run` to exercise that
contract without changing SSM.

## Inputs and outputs
Inputs are the pinned AL2023 image configuration, Proxmox credentials, and the
Packer variable file. Outputs are reusable templates and separate golden/fixture
manifests under `infra/images/packer/manifests/`. The source, golden, and fixture
templates are intentionally separate from Terraform state.

The pinned x86_64 XFS/GPT source has a 25 GiB virtual disk.
`PROXMOX_SOURCE_DISK_SIZE=native` preserves that size and
`PROXMOX_DISK_MAX_SIZE=25G` rejects unexpected growth. Packer full clones keep
the same 25 GiB virtual size. New Terraform full clones inherit it; existing
32 GiB clones are unchanged until deliberately replaced.

AWS has a separate storage contract because an EC2 root volume cannot be
smaller than its AMI snapshot. The official minimal EC2 AMI has a smaller
native snapshot, so FlowForm intentionally expands it to 10 GiB during the
Packer build. CDK declares the same 10 GiB root mapping for app and proxy.

## Failure behaviour
- AL2023 has no supported QEMU guest agent package, so the Proxmox builder uses
  a reserved static build address and explicit SSH host instead of agent-based
  IP discovery.
- The shared golden image deliberately excludes runtime container images. The
  the two fixtures are bounded exceptions for the isolated LocalStack and DB
  VMs; each contains only its declared image layers and an image
  inventory/archive, with no runtime configuration or service state.

## Verification commands
```bash
infra/tests/images/validate.sh
infra/images/scripts/image verify proxmox
```

The validation script assembles each build's nested HCL into a temporary flat
Packer project, runs `packer init` and `packer validate` for both golden
builders and both fixture builders, checks shell syntax, and tests source-template
preparation. It does not create AMIs/templates or prove a live rehearsal.
The disk verifier connects to Proxmox, reports the downloaded file size and
QCOW2 virtual size, reports each configured template size, and fails if any
exceeds the configured maximum.

## Related documents

- [[cloud-deployment|Cloud deployment]]
- [[packer|Packer implementation]]
- [[deployment-model|Deployment model]]
- [[proxmox-rehearsal|Proxmox rehearsal implementation]]
- [[infrastructure-resources|Infrastructure resources]]
