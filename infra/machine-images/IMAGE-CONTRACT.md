# FlowForm machine-image contract

FlowForm uses three machine-image levels:

```text
Base
├── App
└── Proxy
```

## Base

The Base image contains only host-wide capabilities:

- Amazon Linux 2023 and common package updates;
- Docker Engine, containerd, Buildx, and Compose;
- AWS CLI;
- SSM Agent and EC2 Instance Connect support on AWS;
- common host hardening and runtime directories;
- image cleanup and verification.

It must not contain either role bootstrap, a role systemd service, Compose
topology, service configuration, application source, container images,
environment values, release digests, credentials, or secrets. Verification
fails if `/opt/flowform/role`, `/opt/flowform/runtime`, or either role service
is present.

The Base build is also the Proxmox golden template source. Platform-specific
guest setup is restricted to the corresponding Packer builder.

## App and Proxy

Each AWS role image consumes one exact Base AMI ID.

The App image contains:

- shared host helpers;
- the app-only host bootstrap and systemd unit;
- common runtime convergence scripts;
- the AWS App Compose topology copied from `infra/containers/runtime/`.

The Proxy image contains the corresponding proxy-only assets. Verification
rejects assets belonging to the opposite role and records the exact parent Base
AMI.

Neither role image contains container layers, secrets, environment-specific
addresses, or current container release digests.

## Repository ownership

- `infra/machine-images/definitions/` owns Packer definitions and host assets.
- `infra/machine-images/shared/` owns installed common host machinery.
- `infra/containers/images/` owns service software and immutable service
  configuration.
- `infra/containers/runtime/` owns Compose topology and container convergence.
- `infra/contracts/` owns interfaces shared between those release units.
- `infra/deployment/` owns infrastructure creation and operator deployment
  actions.

Copying a runtime file into a role AMI does not transfer repository ownership
of that file to machine-images.

## AWS artifacts

Every successful AWS manifest identifies:

- image role;
- AMI ID;
- source commit;
- region and architecture;
- root snapshot;
- exact parent Base AMI for App and Proxy.

AWS images must have one encrypted gp3 root mapping within the configured
8–12 GiB policy and carry the FlowForm Packer ownership and lineage tags.
Only App and Proxy AMIs are published for CDK consumption.

## Proxmox fixtures

The Proxmox LocalStack and database fixture templates remain deliberate
container-image exceptions. They derive from the clean Proxmox Base template
and preload only images selected by the rehearsal Compose files.

They must not contain runtime Compose files, addresses, credentials, TLS
private keys, seeded service state, role units, or running containers. Their
disk-size and image-inventory protections remain unchanged.
