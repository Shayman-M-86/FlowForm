# Machine-image tooling

`image` is the only public machine-image operator command.

```bash
infra/machine-images/tooling/image --help

infra/machine-images/tooling/image doctor aws
infra/machine-images/tooling/image build aws base
infra/machine-images/tooling/image build aws app
infra/machine-images/tooling/image build aws proxy
infra/machine-images/tooling/image build aws all
infra/machine-images/tooling/image verify aws app
infra/machine-images/tooling/image artifact aws app

infra/machine-images/tooling/image publish aws \
  --environment staging --role app --dry-run
infra/machine-images/tooling/image publish aws \
  --environment staging --role app

infra/machine-images/tooling/image prune aws \
  --environment staging --dry-run
infra/machine-images/tooling/image prune aws \
  --environment staging --apply

infra/machine-images/tooling/image prepare proxmox
infra/machine-images/tooling/image build proxmox all
infra/machine-images/tooling/image verify proxmox
```

Validation-only builds initialize and validate Packer without starting a
builder:

```bash
infra/machine-images/tooling/image build aws all --validate-only
infra/machine-images/tooling/image build proxmox all --validate-only
```

AWS publication and pruning verify the authenticated account against the CDK
environment configuration. Dry-run publication performs all checks without
writing SSM. Dry-run pruning performs read-only inventory and prints the exact
eligible AMIs; it does not use AWS's `--dry-run` flag and therefore does not
report the confusing `DryRunOperation` response.
