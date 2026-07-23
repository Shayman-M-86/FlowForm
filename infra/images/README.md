# FlowForm machine images

`infra/images/scripts/image` is the only operator entry point for building and
checking FlowForm machine images. Packer owns reusable images; Terraform and CDK
consume completed image identifiers and never invoke Packer.

## Quick start

Run commands from the repository root.

```bash
infra/images/scripts/image --help
infra/images/scripts/image doctor proxmox

cp infra/images/config/proxmox-source.env.example \
  infra/images/config/proxmox-source.env
cp infra/images/packer/variables/proxmox.auto.pkrvars.hcl.example \
  infra/images/packer/variables/proxmox.auto.pkrvars.hcl

infra/images/scripts/image prepare proxmox
infra/images/scripts/image prepare proxmox --apply
infra/images/scripts/image build proxmox all
```

The first `prepare` is a read-only preflight. `--apply` creates a missing source
template. Replacing a mismatched source requires the explicit combination
`--apply --replace`; no aggregate build replaces it automatically.

## Common commands

| Goal | Command |
| --- | --- |
| Check prerequisites | `infra/images/scripts/image doctor aws\|proxmox\|all` |
| Build Proxmox golden template 9000 | `infra/images/scripts/image build proxmox golden` |
| Build LocalStack fixture 9001 | `infra/images/scripts/image build proxmox localstack` |
| Build PostgreSQL fixture 9002 | `infra/images/scripts/image build proxmox db` |
| Build and verify all Proxmox images | `infra/images/scripts/image build proxmox all` |
| Validate Packer without building | `infra/images/scripts/image build proxmox all --validate-only` |
| Verify live Proxmox disk policy | `infra/images/scripts/image verify proxmox` |
| Build and verify the AWS AMI | `infra/images/scripts/image build aws` |
| Print the latest AWS AMI ID | `infra/images/scripts/image artifact aws` |
| Verify the latest AWS AMI | `infra/images/scripts/image verify aws` |

Proxmox builds are sequential because all builders share the reserved build IP.
`build proxmox all` performs source preflight, builds golden → LocalStack → DB,
then verifies VMIDs 8999–9002. It does not deploy rehearsal VMs; use
`infra/deployment/proxmox/scripts/rehearsal` afterward.

## AWS and CDK

AWS image publication is tied to the environment contract in
`infra/deployment/aws/cdk/flowform_infra/config/environments.py`. The dispatcher
derives both the region and SSM destination from that CDK configuration:

```bash
cp infra/images/packer/variables/aws.auto.pkrvars.hcl.example \
  infra/images/packer/variables/aws.auto.pkrvars.hcl

export AWS_PROFILE=flowform-dev
aws login --profile "$AWS_PROFILE"

infra/images/scripts/image doctor aws
infra/images/scripts/image build aws
infra/images/scripts/image publish aws --environment staging --dry-run
infra/images/scripts/image publish aws --environment staging
```

Publication verifies the AMI and snapshot contract before overwriting the CDK
environment's `/flowform/<environment>/ec2/baseAmiId` SSM parameter. It requires
an explicit `dev`, `staging`, or `prod` environment; arbitrary parameter names
are not accepted, and publication is refused when the authenticated AWS account
does not match the CDK account. `--dry-run` performs every precheck without
writing SSM.

The AWS path requires real EC2/Packer networking and is not exercised by the
normal structural test suite. CDK consumes the published parameter during stack
synthesis/deployment; image publication does not run `cdk deploy`.

## Configuration and outputs

- `config/proxmox-source.env`: ignored shell configuration for importing the
  pinned AL2023 QCOW2 as source template 8999.
- `packer/variables/proxmox.auto.pkrvars.hcl`: ignored Proxmox Packer values.
- `packer/variables/aws.auto.pkrvars.hcl`: ignored AWS Packer values.
- `packer/manifests/`: Packer artifact manifests consumed by `artifact`,
  `verify`, and `publish`.
- `IMAGE-CONTRACT.md`: allowed image contents and platform differences.
- `packer/README.md`: lower-level HCL layout and image lineage.

An older checkout may still have `infra/images/scripts/.env`. The dispatcher
will use it with a warning; move it without printing its contents:

```bash
mv infra/images/scripts/.env infra/images/config/proxmox-source.env
```

## Logs and failures

Operator messages have UTC timestamps, phases, terminal-aware colors, elapsed
time, and a final result. Set `IMAGE_COLOR=always|auto|never`; `NO_COLOR`
disables ANSI color. Native Packer, AWS, SSH, and remote output remains intact.

Prechecks fail before remote mutation when a tool, configuration value, file,
AWS session, source template, or reserved build address is unavailable. The
error identifies what to correct. Image scripts never print credential files,
API tokens, or AWS credentials.

## Validation

```bash
infra/tests/images/validate.sh
python3 scripts/docs/validate-doc-links.py
python3 scripts/docs/validate-doc-metadata.py
```

The image suite checks Packer formatting/validation, shell syntax, dispatcher
routing, source preparation, AWS artifact validation, CDK parameter mapping,
and removal of legacy public entry points. Live builds remain explicit operator
actions.
