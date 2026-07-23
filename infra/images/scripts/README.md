# Image command cheat sheet

Run these commands from the repository root. `image` is the only operator entry
point for machine-image operations.

```bash
# Show every available command.
infra/images/scripts/image --help

# Check tools, configuration, credentials, connectivity, and source readiness.
infra/images/scripts/image doctor proxmox
infra/images/scripts/image doctor aws

# Check the Proxmox source template without changing anything.
infra/images/scripts/image prepare proxmox

# Create the Proxmox source template when it is missing.
infra/images/scripts/image prepare proxmox --apply

# Deliberately replace a mismatched Proxmox source template.
infra/images/scripts/image prepare proxmox --apply --replace

# Build the complete Proxmox lineage: golden, LocalStack, and DB templates.
infra/images/scripts/image build proxmox all

# Validate every Proxmox Packer definition without building images.
infra/images/scripts/image build proxmox all --validate-only

# Verify the live Proxmox image disk-size contract.
infra/images/scripts/image verify proxmox

# Build and verify the AWS golden AMI.
infra/images/scripts/image build aws

# Print or verify the latest AWS AMI recorded in the Packer manifest.
infra/images/scripts/image artifact aws
infra/images/scripts/image verify aws

# Preview or publish the verified AMI to the SSM parameter owned by CDK.
infra/images/scripts/image publish aws --environment staging --dry-run
infra/images/scripts/image publish aws --environment staging

# Run the complete local/Packer validation suite.
infra/tests/images/validate.sh
```

Use `dev`, `staging`, or `prod` with `publish aws`. Publication does not deploy
CDK; it updates the environment's configured base-AMI parameter for the next
CDK deployment.

For configuration, safety details, and troubleshooting, see
[`infra/images/README.md`](../README.md).
