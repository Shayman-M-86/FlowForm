# Infrastructure ownership map

Each top-level directory answers one ownership question:

| Directory | Question answered | Owns |
| --- | --- | --- |
| `image-factory/` | How are reusable machine images built? | Packer sources, provisioners, manifests, image contract |
| `platforms/` | How does a platform create and manage machines? | AWS CDK and Proxmox host/VM lifecycle scripts |
| `runtime/` | What happens after a machine boots? | Cloud-init, bootstrap, deployment Compose, shared runtime configuration |
| `environments/` | What values and topology differ by deployment? | Development Compose inputs and rehearsal overrides/fixtures |
| `tests/` | How is infrastructure behavior checked? | Test Compose stack and image validation |

The operational flow is:

```text
Machine image → platform → cloud-init → bootstrap → Docker Compose → FlowForm services
```

Local container files deliberately live under `environments/development` and
`tests` because they describe those execution contexts; deployment Compose files
under `runtime/compose` remain the shared post-boot host contract.
