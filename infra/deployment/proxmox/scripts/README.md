# Operating the Proxmox rehearsal

Run these commands from the repository root. `rehearsal` is the only operator
entrypoint for the deployed rehearsal.

## Full rebuild

```bash
infra/deployment/proxmox/scripts/rehearsal build --fresh -- -auto-approve
```

This command:

1. destroys the four Terraform-managed rehearsal VMs;
2. recreates them with Terraform;
3. checks and synchronises required secrets;
4. converges the proxy and prepares the app VM's isolated image relay;
5. converges the database while building the backend and pulling Alloy;
6. publishes only images whose registry config digest is not already current;
7. converges the app; and
8. runs the full non-disruptive verification suite.

It deletes disposable VM, LocalStack, registry, and database state. It does
**not** delete the root-only secret bundle on the PVE host, the Packer templates,
the private bridge, or workstation TLS trust. An existing secret bundle is
fingerprinted before the rebuild and checked afterward.

To converge without destroying healthy VMs, omit `--fresh`:

```bash
infra/deployment/proxmox/scripts/rehearsal build -- -auto-approve
```

## Before running it

- `infra/env/dev/.backend.env` must contain the required non-secret Auth0
  identifiers.
- Provide the Grafana token through `GRAFANA_CLOUD_TOKEN_FILE`,
  `GRAFANA_CLOUD_TOKEN`, or `infra/env/dev/.grafana.env`.
- Provide the Auth0 management secret through `AUTH0_MGMT_SECRET_FILE`,
  `AUTH0_MGMT_SECRET`, or an authenticated AWS CLI session (`aws login`).
- The PVE SSH key defaults to `~/.ssh/proxmox_codex`.
- Run Terraform initialization once if this checkout has not been initialized:

  ```bash
  infra/deployment/proxmox/scripts/rehearsal terraform init
  ```

Missing or empty inputs fail before convergence and print the accepted source
and recovery command. `build --fresh` checks these inputs and required PVE-host
tools before it runs `terraform destroy`.

When no AWS profile is set, `rehearsal` exports `AWS_PROFILE=flowform-dev`. It
checks STS before reading Secrets Manager. If STS specifically confirms that
the session is missing or expired, an interactive run asks whether to run
`aws login`. If `flowform-dev` is an AssumeRole profile, `rehearsal` follows its
`source_profile` chain and logs into the writable base profile instead, then
rechecks STS through `flowform-dev` before continuing.
Profile configuration, network, permission, and missing-secret errors do not
trigger the login prompt; they fail with their actual error instead.

Operator messages use UTC timestamps and terminal-aware colours for phases,
warnings, errors, successful checks, and completion. ANSI colour is omitted
when output is redirected. Set `REHEARSAL_COLOR=always|auto|never` to override
that choice, or set `NO_COLOR` to disable colour. Terraform, Docker, and raw
container payloads retain their native format so interactive prompts and JSON
remain usable.

Every build ends with a summary naming the result, failed phase, and elapsed
time. Verification summaries include the total/pass/fail counts and repeat each
failed check, followed by the exact verification command to rerun.

The usual AWS-login recovery is:

```bash
export AWS_PROFILE=flowform-dev
aws login --profile "$AWS_PROFILE"
```

## Check the result

A successful `rehearsal build` has already run `rehearsal verify`. The commands
below are useful when checking an existing deployment without rebuilding or
when inspecting logs.

```bash
infra/deployment/proxmox/scripts/rehearsal verify
infra/deployment/proxmox/scripts/rehearsal logs app --list
infra/deployment/proxmox/scripts/rehearsal logs app -f
```

Use `rehearsal verify --disruptive` only when intentionally testing failure with
Squid stopped temporarily.

## Other common operations

```bash
# Synchronise secrets without rebuilding.
infra/deployment/proxmox/scripts/rehearsal sync

# Rotate a managed secret family and reconverge its consumers.
infra/deployment/proxmox/scripts/rehearsal rotate app
infra/deployment/proxmox/scripts/rehearsal rotate database
infra/deployment/proxmox/scripts/rehearsal rotate linkage

# Run Terraform directly with the same configuration and SSH preflight as build.
infra/deployment/proxmox/scripts/rehearsal terraform plan
infra/deployment/proxmox/scripts/rehearsal terraform apply

# Show every command.
infra/deployment/proxmox/scripts/rehearsal --help
```

`build --fresh` rebuilds the deployed rehearsal, not the Packer templates. For
a new base or fixture image, rebuild the templates first using the scripts under
`infra/images/scripts/`, then run the full rebuild command above.
