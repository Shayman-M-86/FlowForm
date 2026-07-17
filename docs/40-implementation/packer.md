---
title: Packer implementation
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/images/packer/"
  - "../../infra/images/scripts/"
  - "../../infra/images/IMAGE-CONTRACT.md"
  - "../../infra/deployment/proxmox/terraform/"
  - "../../infra/tests/images/"
related_docs:
  - "Machine image building"
  - "Deployment model"
  - "Proxmox rehearsal implementation"
  - "Infrastructure implementation"
---

# Packer implementation
Maps the current Packer and Proxmox image boundary to its implementation.

## Directory ownership
`infra/images/packer/` owns builds, sources, variables, provisioners, manifests,
locals, and required plugins. Shared steps live in `provisioners/common/`;
platform-only steps live in `provisioners/aws/` and `provisioners/proxmox/`.

`infra/images/scripts/` owns source preparation, selected Packer builds, and AWS
AMI publication. Its common helper creates a temporary flat Packer project
because Packer does not recursively load the canonical nested HCL directories.
Terraform is intentionally outside this ownership boundary under
`infra/deployment/proxmox/terraform/`.

## Entry points
- `prepare-proxmox-source.sh` imports and generalizes the minimal AL2023
  source template while preserving its native disk size by default.
- `verify-proxmox-disk-sizes.sh` reports the downloaded QCOW2 and source,
  golden, and fixture virtual sizes and enforces the configured maximum.
- `build-proxmox-image.sh` builds only the shared Proxmox golden template.
- `build-proxmox-localstack-fixture.sh` builds only the fixture derived from the
  golden template.
- `build-aws-image.sh` builds only the AWS golden AMI; `publish-aws-ami.sh`
  publishes its manifest ID to an explicit SSM parameter.
- `sources/proxmox.pkr.hcl` defines both Proxmox clone sources with an
  explicit reserved SSH address.
- `builds/golden.pkr.hcl` defines the shared build and platform-specific guest
  provisioners.
- `builds/localstack-fixture.pkr.hcl` uploads the maintained Compose inputs only
  for image-reference extraction and runs the fixture preload provisioner.

## Important modules
The shared build installs base packages, Docker/Compose, AWS CLI, host
configuration, and verification requirements. The Proxmox build step configures
the guest serial console. The cleanup step removes image-specific identity and
credential state before template conversion.

The source-preparation path and Packer source disable the QEMU guest agent;
AL2023 does not support it. Packer reaches its temporary clone through the
configured static build IP instead. The fixture provisioner pulls, inspects,
and saves the LocalStack, registry, and TLS-shim images, then stops Docker. It
does not copy Compose or runtime configuration into the resulting template.

The official source QCOW2 is sparse/compressed on disk but declares a 25 GiB
virtual disk containing a GPT layout and XFS root filesystem. `qm importdisk`
preserves that virtual capacity. Source bootstrap expands a filesystem only
when the disk was explicitly enlarged; Packer and Terraform full clones then
inherit the template capacity. The default `native` policy avoids the resize
that previously changed 25 GiB to 32 GiB. XFS is never shrunk in place.

## Dependency direction
Packer consumes a minimal source template and produces the shared golden
outputs; the Proxmox fixture consumes that completed golden template. Terraform
consumes golden and fixture VMIDs and produces deployment VMs. Neither layer
invokes the other. Per-role cloud-init belongs to Terraform, not either image.

## Generated versus handwritten code
Packer variable files containing real credentials and manifests are local or
generated artifacts. Terraform cloud-init payloads are rendered locally from
their maintained templates; Terraform uploads the rendered result but the
rendered files are not committed.

## Tests and validation
`infra/tests/images/validate.sh` runs Packer syntax validation and the
source-template preparation tests, including the native-size no-resize path.
Successful Proxmox build wrappers then run the live disk-size verifier.
Terraform configuration is validated from
`infra/deployment/proxmox/terraform/` with `terraform validate` after its
cloud-init payloads have been rendered.

Static validation resolves the AWS golden, Proxmox golden, and Proxmox fixture
builders. A real fixture build and applied rehearsal remain operator actions;
checked-in validation does not claim they are live or healthy.

## Related documents

- [[Machine image building]]
- [[Deployment model]]
- [[Proxmox rehearsal implementation]]
- [[Infrastructure implementation]]
