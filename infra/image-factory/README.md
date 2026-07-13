# FlowForm image factory

This directory owns the software installed before a FlowForm machine first
boots. It is intentionally platform-independent: one Packer provisioning
pipeline produces either an AWS AMI or a Proxmox template from the same Amazon
Linux 2023 image contract.

```text
image-factory/
├── packer/        Packer sources, build definition, and separated variables
├── provisioners/  shared, AWS-only, and Proxmox-only Packer provisioners
└── manifests/     generated build metadata and the AMI extraction helper
```

`packer/source.aws.pkr.hcl` and `packer/source.proxmox.pkr.hcl` describe only
how their platform supplies a VM. `packer/build.golden.pkr.hcl` is the sole
golden-image construction flow; it invokes the common provisioners and then
the platform agent provisioners.

## Build a Proxmox template

Import the official Amazon Linux 2023 KVM qcow2 once as the minimal Proxmox
source template, then run:

```bash
cd infra/image-factory/packer
cp variables/proxmox.auto.pkrvars.hcl.example proxmox.auto.pkrvars.hcl
# Edit proxmox.auto.pkrvars.hcl, including proxmox_source_template.
packer init .
packer validate -syntax-only .
packer build -only='proxmox-clone.amazon_linux_2023' .
```

`../build-proxmox-template.sh` is the equivalent convenience entry point. It
does not add a separate image-construction path.

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

Run `infra/tests/images/validate.sh` for static Packer and layout validation.
The image contract excludes application code, secrets, mutable container images,
and environment topology; those belong to runtime and environment directories.
