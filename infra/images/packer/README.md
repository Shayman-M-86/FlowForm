# FlowForm Packer image builds

Packer owns reusable machine-image construction. Terraform under
`infra/deployment/` consumes completed image IDs and never runs Packer.

```text
packer/
├── builds/                       shared golden and Proxmox fixture builds
├── sources/                      AWS and Proxmox builders
├── variables/                    variable declarations and local examples
├── provisioners/
│   ├── common/                   shared AL2023, Docker, Compose, and verification
│   ├── aws/                      EC2 and SSM guest setup
│   └── proxmox/                  Proxmox guest and LocalStack fixture steps
├── manifests/                    ignored generated build manifests
├── locals.pkr.hcl
└── plugins.pkr.hcl
```

Packer loads one directory non-recursively. The scripts under
`infra/images/scripts/` therefore assemble the selected canonical HCL files as
links in a temporary flat project, then run `packer init`, `packer validate`,
and only the requested builder. No HCL definition is duplicated.

## Image lineage

```text
shared golden build
├── AWS AMI
└── Proxmox golden template
    └── Proxmox LocalStack fixture template
```

The shared golden build installs Amazon Linux 2023 base dependencies, Docker,
Docker Compose, AWS CLI, common host defaults, platform-specific guest support,
verification, and image cleanup. It contains no application code, runtime
configuration, secrets, or runtime container images.

The Proxmox-only fixture clones the completed golden template and reads image
references from the maintained LocalStack, registry, and TLS-shim Compose
files. It pulls and verifies those exact images so the isolated LocalStack VM
can start without internet access. Cloud-init still supplies the Compose files,
TLS material, service units, networking, and startup actions at boot.

## Proxmox disk sizing

The pinned official x86_64 XFS/GPT AL2023 KVM QCOW2 has a 25 GiB virtual disk.
Source preparation keeps that native size by default; the source, golden, and
fixture templates therefore remain 25 GiB. The fixture currently uses about
4.5 GiB after preloading its images, leaving about 20 GiB for package updates,
Docker temporary data, and logs.

`PROXMOX_SOURCE_DISK_SIZE=native` avoids an unnecessary `qm disk resize`.
`PROXMOX_DISK_MAX_SIZE=25G` is a guardrail applied to the downloaded image and
the source/golden/fixture templates. If a later release is larger, review its
layout and capacity needs before raising the maximum. XFS must not be shrunk in
place; rebuild templates from the original QCOW2 when reducing a prior size.

## Build order

```bash
cp infra/images/scripts/.env.example infra/images/scripts/.env
infra/images/scripts/prepare-proxmox-source.sh
infra/images/scripts/prepare-proxmox-source.sh --apply

cp infra/images/packer/variables/proxmox.auto.pkrvars.hcl.example \
  infra/images/packer/variables/proxmox.auto.pkrvars.hcl
# Fill in the local Proxmox values.
infra/images/scripts/build-proxmox-image.sh
infra/images/scripts/build-proxmox-localstack-fixture.sh
infra/images/scripts/verify-proxmox-disk-sizes.sh

cd infra/deployment/proxmox/terraform
terraform init
terraform validate
terraform plan
```

For AWS, copy the AWS variable example and run
`infra/images/scripts/build-aws-image.sh`. To publish the resulting manifest AMI
ID to the CDK configuration parameter, run:

```bash
infra/images/scripts/publish-aws-ami.sh /flowform/staging/ec2/baseAmiId ap-southeast-2
```

See `infra/images/IMAGE-CONTRACT.md` for the allowed image contents.
