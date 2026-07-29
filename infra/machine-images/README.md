# FlowForm machine images

This directory owns host images and the tooling used to build them. It does not
own container images or Compose topology.

```text
machine-images/
├── definitions/
│   ├── base/                 base AMI and Proxmox golden definition
│   ├── app/                  App AMI and app-only host assets
│   └── proxy/                Proxy AMI and proxy-only host assets
├── shared/
│   ├── host-assets/          common files installed on role hosts
│   └── provisioners/         role-image installation and verification
├── packer/                   shared sources, variables, plugins, and manifests
├── tooling/                  the operator-facing `image` command
└── config/                   ignored/local image-builder configuration
```

Container deployment topology belongs under
`infra/containers/runtime/`. App and Proxy Packer builds copy the relevant
runtime assets into the completed role AMI, but machine-images does not own
those source files.

## AWS lineage

```text
official minimal Amazon Linux 2023
└── FlowForm Base AMI
    ├── FlowForm App AMI
    └── FlowForm Proxy AMI
```

The Base AMI contains only common host capabilities. CDK never launches it.
App and Proxy AMIs consume its exact AMI ID and record that parent in both the
Packer manifest and AWS tags.

Run from the repository root:

```bash
infra/machine-images/tooling/image doctor aws
infra/machine-images/tooling/image build aws all
infra/machine-images/tooling/image verify aws app
infra/machine-images/tooling/image verify aws proxy

infra/machine-images/tooling/image publish aws \
  --environment staging --role app --dry-run
infra/machine-images/tooling/image publish aws \
  --environment staging --role app
infra/machine-images/tooling/image publish aws \
  --environment staging --role proxy
```

Publication writes only deployable role parameters:

```text
/flowform/<environment>/ec2/appAmiId
/flowform/<environment>/ec2/proxyAmiId
```

The transitional `baseAmiId` mapping remains readable by tooling while the
old deployment path is being retired, but Base AMIs cannot be published by the
role publication command.

AMI cleanup is always explicit:

```bash
infra/machine-images/tooling/image prune aws \
  --environment staging --dry-run
infra/machine-images/tooling/image prune aws \
  --environment staging --apply
```

Pruning protects all environment AMI parameters, AMIs used by non-terminated
instances, the two newest successful App and Proxy builds, and the exact Base
AMI parent of every protected role AMI. The command considers only available,
self-owned images tagged `project=flowform` and `managed_by=packer`.

## Proxmox compatibility

The existing Proxmox golden and fixture workflow remains available:

```bash
cp infra/machine-images/config/proxmox-source.env.example \
  infra/machine-images/config/proxmox-source.env
cp infra/machine-images/packer/variables/proxmox.auto.pkrvars.hcl.example \
  infra/machine-images/packer/variables/proxmox.auto.pkrvars.hcl

infra/machine-images/tooling/image prepare proxmox
infra/machine-images/tooling/image prepare proxmox --apply
infra/machine-images/tooling/image build proxmox all
```

Proxmox uses the Base definition as its golden template. Its LocalStack and
database fixture definitions continue to preload the explicitly declared
rehearsal images.

## Installed role layout

```text
/opt/flowform/
├── host/bin/                 shared host helpers
├── role/bin/                 one role bootstrap only
└── runtime/
    ├── common/scripts/       release selection and role convergence
    └── compose/              one role Compose topology
```

Systemd starts `flowform-app.service` or `flowform-proxy.service`. The service
loads `/etc/flowform/instance-context.json`, resolves the role release manifest,
then invokes the baked role bootstrap.

## Validation

```bash
infra/tests/images/validate.sh
```

The suite checks structure and executable bits, shell syntax, Packer formatting
and validation, role isolation, AWS manifest verification, prune protections,
and the retained Proxmox definitions. It does not build, publish, or delete any
live AWS resource.
