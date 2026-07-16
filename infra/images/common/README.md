# FlowForm image factory

This directory owns the software installed before a FlowForm machine first
boots. It is intentionally platform-independent: one Packer provisioning
pipeline produces either an AWS AMI or a Proxmox template from the same Amazon
Linux 2023 image contract.

```text
images/
├── packer/                    consolidated Packer HCL (all sources, golden build,
│                              locals, variables) + init/ entry points
├── common/build-steps/        shared build steps + lib.sh
├── aws/build-steps/           AWS-only build steps
├── proxmox/build-steps/       Proxmox-only build steps
└── common/manifests/          generated build metadata + AMI extraction helper
    aws/manifests/             AWS extractor that reads the shared manifest
```

`packer/source.aws.pkr.hcl` and `packer/source.proxmox.pkr.hcl` describe only
how their platform supplies a VM. `packer/build.golden.pkr.hcl` is the sole
golden-image construction flow; it invokes the common build steps and then
the platform-specific build steps. All `.pkr.hcl` live in one `packer/` dir so a
single `packer build` loads the full config.

## Build a Proxmox template

Prepare the official Amazon Linux 2023 KVM qcow2 as the minimal Proxmox source
template, reserve one unused LAN address outside the DHCP pool for the temporary
Packer VM, then run:

```bash
cp infra/images/proxmox/.env.example infra/images/proxmox/.env
# Edit the Proxmox source-template values.
infra/images/proxmox/provisioning/01-prepare-proxmox-source.sh
infra/images/proxmox/provisioning/01-prepare-proxmox-source.sh --apply
cd infra/images/packer
cp variables/proxmox.auto.pkrvars.hcl.example proxmox.auto.pkrvars.hcl
# Edit the file, including the source template and dedicated build IP/gateway.
../proxmox/provisioning/02-build-proxmox-template.sh
```

`../proxmox/provisioning/02-build-proxmox-template.sh` initializes, validates, and runs the consolidated
Packer build. It also refuses to start when the dedicated build address responds
to ping. The Proxmox builder uses that explicit address because AL2023 does not
provide a supported QEMU guest agent. Deployment replaces the temporary network
metadata when cloning the completed template.

## Build an AWS AMI

```bash
cd infra/image-factory/packer
cp variables/aws.auto.pkrvars.hcl.example aws.auto.pkrvars.hcl
# Edit aws.auto.pkrvars.hcl with AWS network/profile values.
packer init .
packer validate -syntax-only .
packer build -only='flowform-golden.amazon-ebs.amazon_linux_2023' .
```

Packer writes `infra/image-factory/manifests/packer-manifest.json`. Publish
the extracted AMI ID to the explicit environment SSM parameter consumed by
`infra/deployment/aws/cdk`:

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
