# FlowForm image factory

This directory owns the software installed before a FlowForm machine first
boots. It is intentionally platform-independent: one Packer provisioning
pipeline produces either an AWS AMI or a Proxmox template from the same Amazon
Linux 2023 image contract.

```text
images/
├── packer/                    consolidated Packer HCL (all sources, golden build,
│                              locals, variables) + build-proxmox-template.sh
├── common/build-steps/        shared build steps + lib.sh
├── aws/build-steps/           AWS-only build steps
├── proxmox/build-steps/       Proxmox-only build steps
└── common/manifests/          generated build metadata + AMI extraction helper
    aws/manifests/             AWS extractor that reads the shared manifest
```

`packer/source.aws.pkr.hcl` and `packer/source.proxmox.pkr.hcl` describe only
how their platform supplies a VM. `packer/build.golden.pkr.hcl` is the sole
golden-image construction flow; it invokes the common build steps and then
the platform agent build steps. All `.pkr.hcl` live in one `packer/` dir so a
single `packer build` loads the full config.

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
