# Shared Packer plumbing

Packer definitions are split by ownership:

```text
infra/machine-images/
├── definitions/
│   ├── base/build.pkr.hcl
│   ├── app/build.pkr.hcl
│   └── proxy/build.pkr.hcl
└── packer/
    ├── builds/               Proxmox-only fixture builds
    ├── sources/              reusable AWS and Proxmox builders
    ├── variables/            declarations and ignored local values
    ├── provisioners/         Proxmox-specific fixture steps
    ├── manifests/            ignored generated artifact records
    ├── locals.pkr.hcl
    └── plugins.pkr.hcl
```

Packer loads a directory non-recursively. The
`infra/machine-images/tooling/image` command assembles the selected definition
and shared HCL into a temporary flat project before running `packer init`,
`packer validate`, and the requested builder.

## AWS build order

```text
build Base
→ verify Base
→ read exact Base AMI ID
→ build App and Proxy from that ID
→ verify role contents and lineage
```

`image build aws all` enforces that sequence. Building only App or Proxy reads
and verifies the most recent completed Base manifest before starting the child
build.

## Proxmox build order

```text
prepare source template 8999
→ build Base/golden template 9000
→ build LocalStack fixture 9001
→ build database fixture 9002
→ verify disk policy and lineage
```

All Proxmox builders remain sequential because they share the reserved build
address.

Use the operator command rather than invoking these HCL fragments directly:

```bash
infra/machine-images/tooling/image build aws all --validate-only
infra/machine-images/tooling/image build proxmox all --validate-only
```
