# FlowForm image factory

This directory owns the software installed before a FlowForm machine first
boots. It is intentionally platform-independent: one Packer provisioning
pipeline produces either an AWS AMI or a Proxmox template from the same Amazon
Linux 2023 image contract.

```text
image-factory/
├── packer/        Packer sources, build definition, and separated variables
├── provisioners/  shared, AWS-only, and Proxmox-only Packer provisioners
├── sources/       pinned upstream source-image identity and checksum
└── manifests/     generated build metadata and the AMI extraction helper
```

`packer/source.aws.pkr.hcl` and `packer/source.proxmox.pkr.hcl` describe only
how their platform supplies a VM. `packer/build.golden.pkr.hcl` is the sole
golden-image construction flow; it invokes the common provisioners and then
the platform agent provisioners.

## Build a Proxmox template

Create a dedicated Proxmox Packer token and temporary build SSH key. Store the
one-time token value in a mode-`0600` file outside the repository, then prepare
the pinned and checksum-verified source template:

```bash
export PROXMOX_PACKER_SSH_PRIVATE_KEY_FILE=/secure/path/packer-build
infra/image-factory/prepare-proxmox-source.sh \
  --source-vmid 9000 \
  --upload root@pve.example.lan
```

Copy and edit the non-secret example, then build a new immutable candidate VMID:

```bash
cp infra/image-factory/packer/variables/proxmox.auto.pkrvars.hcl.example \
  infra/image-factory/packer/proxmox.auto.pkrvars.hcl
export PROXMOX_TOKEN_SECRET_FILE=/secure/path/proxmox-packer-token
infra/image-factory/build-proxmox-template.sh \
  --vmid 9100 \
  --var-file infra/image-factory/packer/proxmox.auto.pkrvars.hcl \
  --verify-on root@pve.example.lan
```

The wrapper validates API access and visible resources, runs full Packer
validation, builds the candidate, smoke-clones it through QEMU guest agent, and
writes a selectable manifest under `infra/.generated/image-factory/`.

## Build an AWS AMI

```bash
cd infra/image-factory/packer
cp variables/aws.auto.pkrvars.hcl.example aws.auto.pkrvars.hcl
# Edit aws.auto.pkrvars.hcl with AWS network/profile values.
packer init .
packer validate -syntax-only .
packer build -only='amazon-ebs.amazon_linux_2023' .
```

Packer writes `infra/image-factory/manifests/packer-manifest.json`. Publish
the extracted AMI ID to the explicit environment SSM parameter consumed by
`infra/platforms/aws/cdk`:

```bash
AMI_ID="$(infra/image-factory/manifests/extract-aws-ami-id.sh)"
aws ssm put-parameter \
  --name /flowform/staging/ec2/baseAmiId \
  --type String \
  --value "${AMI_ID}" \
  --overwrite
```

Run the infrastructure image validation wrapper available in the active test
layout for static Packer and layout validation.
The image contract excludes application code, secrets, mutable container images,
and environment topology; those belong to runtime and environment directories.
