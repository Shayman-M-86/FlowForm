# FlowForm machine images

Reusable image construction lives here, outside any single environment. Packer
builds one Amazon Linux 2023 host image contract and emits it as either:

- a Proxmox template for local environments, or
- an AWS AMI for CDK-managed environments.

See `IMAGE-CONTRACT.md` for the exact build-time/runtime boundary.

## Layout

```text
infra/images/
├── packer/          # Packer HCL2 builders and variables
├── provisioning/    # shared and platform-specific shell provisioners
└── manifests/       # generated Packer manifests and AMI extraction helper
```

## Proxmox build

Proxmox uses the same Amazon Linux 2023 operating system as AWS. Import the
official Amazon Linux 2023 KVM qcow2 image once as a minimal Proxmox base
template, then let Packer clone and provision it into the FlowForm golden
image.

```bash
cd infra/images/packer
cp variables/local.auto.pkrvars.hcl.example local.auto.pkrvars.hcl
# edit local.auto.pkrvars.hcl, including proxmox_source_template
packer init .
packer validate -syntax-only .
packer build -only='proxmox-clone.amazon_linux_2023' .
```

## AWS AMI build

```bash
cd infra/images/packer
cp variables/aws.auto.pkrvars.hcl.example aws.auto.pkrvars.hcl
# edit aws.auto.pkrvars.hcl with AWS network/profile values
packer init .
packer validate -syntax-only .
packer build -only='amazon-ebs.amazon_linux_2023' .
```

Packer writes `infra/images/manifests/packer-manifest.json`. Extract the AMI ID
and publish it to the SSM parameter consumed by CDK:

```bash
AMI_ID="$(infra/images/manifests/extract-aws-ami-id.sh)"
aws ssm put-parameter \
  --name /flowform/staging/ec2/baseAmiId \
  --type String \
  --value "${AMI_ID}" \
  --overwrite
```

Use the matching environment parameter (`/flowform/prod/ec2/baseAmiId`, etc.)
for each deployment. CDK consumes this explicit Packer image reference; it must
not fall back to an unrelated latest base AMI.

## Static validation

```bash
infra/tests/images/inspect-layout.sh
cd infra/images/packer
packer fmt -check -recursive .
packer init .
packer validate -syntax-only .
```

No command here should bake app secrets, app code, registry credentials, TLS keys
for real environments, or mutable app container images into the host image.
