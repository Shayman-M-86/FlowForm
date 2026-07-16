---
title: Runtime containers
document_type: architecture
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, frontend, infrastructure]
related_code:
  - "../../infra/environments/development/compose/docker-compose.dev.yml"
  - "../../infra/tests/compose/docker-compose.test.yml"
  - "../../infra/environments/development/compose/docker-compose.ec2.local.yml"
  - "../../frontend/docker-compose.dev.yml"
  - "../../infra/runtime/compose/"
  - "../../infra/runtime/bootstrap/"
  - "../../infra/environments/rehearsal/compose/"
related_docs:
  - "Component map"
  - "Deployment model"
  - "Local infrastructure"
  - "Testing workflow"
  - "Secrets and configuration"
  - "Infrastructure implementation"
  - "Services and ports"
---

# Runtime containers

Describes the service groupings and communication boundaries declared by the
current Compose and bootstrap definitions. Exact commands, ports, and file
ownership belong in the linked workflow, implementation, and reference pages.

## Runtime variants

The repository does not use one Compose model unchanged in every context.

| Context | Declared containers | Architectural purpose |
| --- | --- | --- |
| Backend development | Flask development backend, core PostgreSQL, response PostgreSQL | Runs the API and both persistence models on one developer machine with source and development-state mounts. |
| Frontend development | Astro public site, Vite Studio app, optional Studio preview | Provides containerised frontend development independently of the backend Compose project. |
| Backend test | Long-running backend test container, core PostgreSQL, response PostgreSQL | Gives tests an isolated application image and two disposable database services; CI enters the running backend container to execute the suite. |
| Split-runtime local proof | Caddy, Squid, Gunicorn backend, core PostgreSQL, response PostgreSQL | Exercises the proxy/app communication and hardening shape on one Docker host. It is explicitly a workstation proof, not the cloud topology. |
| Shared host runtime | Caddy and Squid on a proxy host; Gunicorn backend on a separate app host | Defines the staging/prod container contract. PostgreSQL and the static frontends are outside these Compose projects. |
| Proxmox rehearsal | Shared proxy/app Compose files plus rehearsal overrides and fixture services | Exercises the shared host bootstrap and images on local VMs while replacing cloud-only dependencies with local equivalents. |

The development and test definitions are operationally useful variants, not
evidence that their networks, credentials, writable mounts, or database
placement match the shared host runtime. See [[Local infrastructure]] and
[[Testing workflow]] for their workflows.

## Shared host boundaries

The declared cloud-oriented runtime is split across two hosts and two Compose
projects:

- The public proxy host runs Caddy for inbound TLS and reverse proxying, and
  Squid as the app host's controlled outbound HTTP(S) proxy.
- The private app host runs only the Flask application under Gunicorn. It binds
  the backend to the host's private interface, reads non-secret configuration
  from a bootstrap-rendered environment file, and receives secrets as mounted
  files.
- The app host reaches the proxy for permitted external HTTP(S) traffic and is
  expected to reach PostgreSQL outside the Compose project. The shared app
  Compose file does not create database containers.
- The public site and Studio are built as static assets for the declared cloud
  deployment; they are not served from either host Compose project.

Both host Compose files harden their application containers with read-only
filesystems, reduced Linux capabilities, `no-new-privileges`, bounded local log
rotation, and memory-backed writable paths where needed. These settings are
observable controls, not a complete statement of the [[Security model]].

## Bootstrap and configuration boundary

Host bootstrap is outside the container images. The proxy bootstrap renders its
Compose environment from SSM plus host-known addresses. The app bootstrap
configures forced proxy egress, materialises Secrets Manager values into a host
`tmpfs`, renders non-secret configuration from SSM, and then starts Compose.
Staging and prod are intended to consume the same base Compose and bootstrap
files with environment-specific values. See [[Secrets and configuration]] for
the configuration lifecycle and [[Infrastructure implementation]] for source
locations.

## Rehearsal boundary

The Proxmox rehearsal reuses the shared host runtime but deliberately changes
dependencies that cannot operate on its offline private network. Its proxy
override substitutes local TLS and egress allow-list configuration. Its app
override adds ephemeral core and response PostgreSQL containers because the
rehearsal does not exercise RDS. Third-party, PostgreSQL, and backend images are
prepared as a digest/checksum-locked offline bundle rather than pulled during
first boot.

Topology creation leaves all rehearsal VMs stopped. Explicit activation starts
the proxy first, then loads and starts the registry, LocalStack, and TLS shim on
the fixtures VM, seeds the local AWS contract, and starts the app VM only after
those prerequisites are healthy. Verification checks both Compose layers,
direct and proxied readiness, and the app VM's lack of a default route. These
are checked-in contracts with mock ordering coverage; real Proxmox acceptance
remains pending. A green live rehearsal would support the shared
image/bootstrap/Compose contract, but would not prove AWS networking, managed
database connectivity, public DNS, or certificate issuance. See
[[Machine image building]] and [[Deployment model]].

## Declared versus running state

This page describes checked-in definitions only. It does not establish which
Compose projects are running on a developer machine or any host. It also does
not establish that the cloud-oriented host runtime has been bootstrapped in AWS;
the current CDK application creates EC2 instances but does not attach the
runtime bootstrap as instance user data. That implementation gap is tracked in
[[Deployment model]].

## Open questions

- Which runtime variant, if any, matches the currently running production API?
- What mechanism will install or update the shared runtime files on provisioned
  EC2 hosts before invoking bootstrap?
- How will backend image publication and host restart be coordinated and rolled
  back once the backend deployment workflow exists?
- Which container images will be pinned by digest rather than mutable tags in
  the deployed environment?

## Related documents

- [[Component map]]
- [[Deployment model]]
- [[Local infrastructure]]
- [[Testing workflow]]
- [[Secrets and configuration]]
- [[Infrastructure implementation]]
- [[Services and ports]]
