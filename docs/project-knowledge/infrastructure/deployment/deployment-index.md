---
title: Deployment architecture
aliases: ["Deployment architecture", "Deployment documentation", "Deployment model", "AWS network topology", "Cloud deployment", "AWS staging bring-up"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure, ci-cd]
related_code:
  - "../../../../infra/deployment/aws/cdk/app.py"
  - "../../../../infra/deployment/aws/operations/README.md"
change_triggers:
  - "../../../../infra/deployment/aws/"
  - "../../../../infra/deployment/bootstrap/"
  - "../../../../.github/workflows/"
related_docs: ["Infrastructure knowledge", "Container runtime", "Machine images", "Proxmox rehearsal", "Configuration and secrets", "Deployment design forces", "External platform boundaries", "Release recovery and readiness"]
---

# Deployment architecture

Deployment joins declared environment topology, promoted immutable artifacts,
runtime configuration, and host convergence. These are separate decisions: an
artifact can exist without being selected by an environment, and a declared
environment can exist without showing that its hosts are healthy.

```text
environment declaration + network boundary
                    |
published machine/container artifacts
                    |
                    v
          selected release and configuration
                    |
                    v
              host convergence
                    |
                    v
             environment verification
```

## AWS operator-facing operations model

AWS deployment work is exposed through one operator-facing operations area.
Its entry points are thin coordinators that can be invoked from a developer
workstation or an automated CLI workflow. They validate the requested action
and delegate to the image, container, deployment, configuration, or host
implementation that owns it.

```text
operator or automated workflow
             |
             v
 centralized AWS operations surface
      |          |          |
      v          v          v
  artifacts   topology   running hosts
 build/select  deploy     converge/verify/recover
      \          |          /
       +---- owning implementations
```

This gives operators a consistent place to discover AWS infrastructure actions
without creating a second implementation layer. The operations area owns
workflow boundaries and safety checks; Packer, container tooling, deployment
code, and host automation continue to own execution details. Its README and
command help are authoritative for which actions are currently available.
Proxmox retains its separate rehearsal lifecycle.

## AWS boundary

AWS deployment code owns the cloud topology, including the separation between
public ingress/proxy responsibilities and private application and data
responsibilities. Network controls, service identity, and runtime policy each
contribute to that boundary; no single layer establishes application security
or service health.

### Network topology at a glance

The durable topology is a trust and traffic model, not a resource inventory.
Inbound traffic crosses a public edge before reaching private application and
data responsibilities. Outbound application traffic uses an explicitly
controlled path to approved external dependencies. Deployment, artifact,
configuration, secret, and management services form a separate control plane.

```text
internet clients
       |
       v
public ingress / proxy
       |
       v
private application ----> controlled outbound access
       |                         |
       v                         v
private data              external dependencies

deployment control plane ---> artifacts, configuration, secrets, management
```

This overview explains the intended boundary only. The current deployment
source owns exact network construction, addressing, service placement, and
environment-specific exceptions. A listener declared by a container is runtime
intent; deployment networking determines whether it is externally reachable.

The AWS operations layer deliberately distinguishes image and container
publication, release promotion, environment deployment, and convergence of
already deployed hosts. Exact command sequences, account prerequisites, and
recovery procedures change with the implementation and belong next to those
operations.

## Design and lifecycle

[[design-forces-and-evolution|Deployment design forces]] explains the cost,
isolation, availability, and operator-effort trade-offs that shape the initial
AWS posture, along with the signals that should trigger evolution. It also
distinguishes environment topology from artifact, configuration, state, and
external-service lifecycles.

[[external-platform-boundaries|External platform boundaries]] separates
declared infrastructure from imported foundations, configured providers, and
human-authorized capabilities. [[release-recovery-and-readiness|Release
recovery and readiness]] describes how those boundaries participate in
release, verification, rollback, and recovery without claiming that the whole
lifecycle is automated today.

## Other environments

The local Proxmox rehearsal has a separate lifecycle and topology, but consumes
the same broad artifact and runtime boundaries. Development and test
environments are separate local compositions, not smaller versions of a cloud
deployment.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[containers-index|Container runtime]]
- [[images-index|Machine images]]
- [[proxmox-index|Proxmox rehearsal]]
- [[configuration|Configuration and secrets]]
- [[design-forces-and-evolution|Deployment design forces]]
- [[external-platform-boundaries|External platform boundaries]]
- [[release-recovery-and-readiness|Release recovery and readiness]]
