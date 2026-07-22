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

Packer loads one directory non-recursively. The
`infra/images/scripts/image` dispatcher therefore assembles selected HCL files as
links in a temporary flat project, then run `packer init`, `packer validate`,
and only the requested builder. No HCL definition is duplicated.

## Image lineage

```text
shared provisioning contract
├── official minimal AL2023 EC2 AMI -> AWS golden AMI (10 GiB)
└── official AL2023 KVM QCOW2 -> Proxmox golden template (25 GiB)
    ├── Proxmox LocalStack fixture template (9001)
    └── Proxmox PostgreSQL fixture template (9002)
```

The shared golden build installs Amazon Linux 2023 base dependencies, Docker,
Docker Compose, AWS CLI, common host defaults, platform-specific guest support,
verification, and image cleanup. It contains no application code, runtime
configuration, secrets, or runtime container images.

The AWS builder uses Amazon's native minimal AL2023 EC2 AMI with kernel 6.1.
It does not import the Proxmox QCOW2. Its 10 GiB encrypted gp3 root is an
AWS-specific cost and capacity policy; successful builds verify that the AMI
and root snapshot retain exactly that size. CDK declares the same mapping.

The Proxmox-only fixtures clone the completed golden template. Template 9001 reads image
references from the maintained LocalStack, registry, and TLS-shim Compose
files. It pulls and verifies those exact images so the isolated LocalStack VM
can start without internet access. Cloud-init still supplies the Compose files,
TLS material, service units, networking, and startup actions at boot.

Template 9002 independently reads the rehearsal DB Compose file and preloads
only its PostgreSQL image. The DB VM has no gateway and Compose uses
`pull_policy: never`, so PostgreSQL never reaches the registry at runtime.

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
cp infra/images/config/proxmox-source.env.example infra/images/config/proxmox-source.env
infra/images/scripts/image prepare proxmox
infra/images/scripts/image prepare proxmox --apply

cp infra/images/packer/variables/proxmox.auto.pkrvars.hcl.example \
  infra/images/packer/variables/proxmox.auto.pkrvars.hcl
# Fill in the local Proxmox values.
infra/images/scripts/image build proxmox all
infra/images/scripts/image verify proxmox

cd infra/deployment/proxmox/terraform
terraform init
terraform validate
terraform plan
```

For AWS, copy the AWS variable example and run
`infra/images/scripts/image build aws`. The dispatcher accepts only a minimal
AL2023 source and an 8–12 GiB root, then verifies the AMI against the
completed artifact. To publish the resulting manifest AMI ID to the CDK
configuration parameter, run:

```bash
infra/images/scripts/image publish aws --environment staging --dry-run
infra/images/scripts/image publish aws --environment staging
```

See `infra/images/IMAGE-CONTRACT.md` for the allowed image contents.
