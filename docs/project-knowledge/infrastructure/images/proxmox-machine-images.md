---
title: Proxmox machine images
aliases: ["Proxmox machine images", "Proxmox image lineage", "Proxmox rehearsal templates"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:95ce9651e774d8e2b1e592f4681167e16e9d479946c6715ff7e3cdd1115cbe24
last_edited: 2026-08-04
tags: [infrastructure]
related_code:
  - "../../../../infra/machine-images/config/proxmox-source.env.example"
  - "../../../../infra/machine-images/packer/variables/proxmox.auto.pkrvars.hcl.example"
  - "../../../../infra/machine-images/packer/sources/proxmox.pkr.hcl"
  - "../../../../infra/machine-images/definitions/base/build.pkr.hcl"
  - "../../../../infra/machine-images/packer/builds/localstack-fixture.pkr.hcl"
  - "../../../../infra/machine-images/packer/builds/db-fixture.pkr.hcl"
  - "../../../../infra/machine-images/tooling/lib/cmd_prepare.sh"
change_triggers:
  - "../../../../infra/machine-images/"
  - "../../../../infra/deployment/proxmox/"
  - "../../../../infra/containers/runtime/proxmox/"
related_docs: ["Machine images", "Proxmox rehearsal", "Container runtime", "Configuration and secrets"]
---

# Proxmox machine images

The Proxmox image path creates a local Amazon Linux 2023 lineage for the
rehearsal environment. It separates importing an official operating-system
source, installing FlowForm's shared host capability, and preloading the narrow
fixture dependencies used by isolated rehearsal services.

```text
official Amazon Linux 2023 KVM image
                  |
                  v
        reusable source template
                  |
                  v
       FlowForm golden template
          /                 \
         v                   v
 LocalStack fixture      database fixture
```

The checked-in defaults reserve separate VM identifiers for the reusable
source, golden template, LocalStack fixture, and database fixture. Those
identifiers and names are configuration, not proof that the corresponding
templates currently exist on a Proxmox host.

## Source preparation and credentials

Source preparation imports the pinned official KVM image and creates the
reusable Proxmox template from which Packer clones. The source configuration
pins the Amazon Linux release, filename, URL, and checksum together, preserves
the official image's native disk size by default, and applies an explicit disk
size ceiling.

Two local credential surfaces serve different operations:

| Surface | Used for | Storage boundary |
| --- | --- | --- |
| Root SSH target and identity | Importing and preparing the reusable source template on the Proxmox host | Authentication stays in the operator's SSH agent or configuration; the local environment file contains no password or private-key material. |
| Proxmox API token | Packer cloning and template builds | The populated Packer variables file is machine-local and ignored by Git. |

The repository supplies examples for both surfaces. Populated copies are local
operator inputs and must not be committed.

## Golden and fixture templates

The golden template receives the same common FlowForm host capability as the
AWS base, plus Proxmox-specific guest setup. It remains role-neutral: it does
not contain application or proxy services, runtime Compose definitions,
environment configuration, credentials, or a selected release.

Fixture templates clone the golden template and are deliberate exceptions to
the usual rule that machine images contain no container layers. Each build
temporarily copies the relevant rehearsal fixture definitions, pulls only the
declared container images, removes the temporary definitions, and records its
artifact metadata. The LocalStack fixture and database fixture remain separate
so their dependency inventories and disk costs can be checked independently.

Fixture templates must not contain running containers, runtime state, network
addresses, credentials, TLS private keys, application/proxy role units, or the
rehearsal's live Compose topology. Deployment still owns VM creation and
runtime startup.

## Sequential build constraint

Proxmox Packer builds use one reserved build address outside the DHCP pool.
Only one build may use it at a time, so the golden and fixture builds are
sequential. The temporary build network metadata is replaced by deployment;
it is not the address contract of a running rehearsal VM.

The stable lineage order is source preparation, golden-template build and
verification, then fixture builds and verification. The machine-image operator
tool owns the exact commands and performs Packer initialization and validation
before a requested build.

## Verification boundary

Repository checks cover the source import contract, template ancestry,
reserved identifiers, disk policy, guest configuration, fixture Compose
references, and the declared image preload behavior. Validation-only execution
does not contact Proxmox or create templates. A live build and the rehearsal's
own verification are still required to establish that templates are usable and
the resulting environment is healthy.

## Related documents

- [[images-index|Machine images]]
- [[proxmox-index|Proxmox rehearsal]]
- [[containers-index|Container runtime]]
- [[configuration|Configuration and secrets]]
