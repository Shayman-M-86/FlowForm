---
title: AWS staging runtime convergence
aliases: ["AWS staging runtime convergence"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, configuration, security]
related_code:
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/application_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py"
  - "../../../infra/deployment/bootstrap/"
  - "../../../infra/containers/strategies/aws/"
  - "../../../infra/images/packer/"
related_docs:
  - "Engineering planning"
  - "AWS CDK staging plan"
  - "AWS staging bring-up"
  - "AWS network topology"
---

# AWS staging runtime convergence

> Current implementation plan after the first Application deployment.

## Checkpoint

The staging infrastructure exists and both EC2 instances are running from the
published FlowForm AMI. AWS infrastructure health checks pass, but they only
show that the virtual machines and EBS volumes are operational.

The last inspected runtime state was:

| Component | State | Meaning |
| --- | --- | --- |
| Proxy EC2 | Running; EC2 checks pass | Host infrastructure is healthy |
| Caddy, Squid, and proxy Alloy | Running | Proxy bootstrap reached its container phase |
| Public API TLS | Failing | ACME DNS-01 validation observed the challenge before the TXT record was available |
| App EC2 | Running; EC2 checks pass | Host infrastructure is healthy |
| App SSM Agent | Offline | The app instance role cannot establish the Systems Manager managed channel |
| Backend container | Restarting or unhealthy | Exact startup error is not yet available because app-host access is broken |
| App Alloy | Running | Local collector health does not yet prove remote log access |
| EC2 Instance Connect recovery | Not working | The AMI does not yet provide a proven EICE login path |

CloudFormation success is therefore only an infrastructure checkpoint, not a
successful application deployment.

## Immediate blockers

### 1. Restore app-host Systems Manager access

Give the application instance role the exact Systems Manager managed-instance
channel permissions it requires. Keep the existing proxy configuration for the
SSM Agent:

```text
HTTP_PROXY=http://10.42.0.4:3128
HTTPS_PROXY=http://10.42.0.4:3128
NO_PROXY=169.254.169.254,localhost,127.0.0.1
```

Deploy the Security stack and verify that the existing app instance becomes a
managed online node. This change should not require an AMI rebuild or host
replacement.

### 2. Diagnose backend convergence

Once SSM works:

1. inspect cloud-init and bootstrap service status;
2. inspect the backend container state and recent logs;
3. correct the smallest verified startup fault;
4. prove backend readiness locally on the app host;
5. prove IAM-token connections to both logical RDS databases.

Do not guess at the backend failure before the logs are available.

### 3. Correct public TLS

The Caddy DNS-01 configuration must allow Route 53 TXT propagation before CA
validation. Disabling propagation waiting caused an observed `NXDOMAIN` for
the ACME challenge and is not a valid staging configuration.

Choose a bounded propagation delay or timeout supported by the Route 53 issuer,
rebuild the relevant image or AMI if its owning artifact requires it, and prove:

- the TXT challenge becomes visible;
- Caddy obtains and retains the certificate;
- the public API endpoint completes TLS;
- the readiness path returns a healthy response.

### 4. Establish a recovery path

Make EC2 Instance Connect through the existing endpoint work for the app host.
The golden image must install and configure the required support, and image
cleanup must remove Packer's temporary SSH key from
`/home/ec2-user/.ssh/authorized_keys`.

Verify EICE access after a fresh host replacement. SSM remains the normal
management path; EICE is the recovery path.

## Operational follow-up

### Fixed-address replacement

Both hosts use fixed private addresses. CloudFormation cannot create a
replacement instance at an address still owned by the old instance. Until the
design changes, an AMI replacement requires:

1. confirm the new AMI and image digests are published;
2. terminate the existing proxy and app instances;
3. wait until both are fully terminated;
4. deploy `FlowForm-Staging-Application` with `--exclusively`;
5. verify complete runtime convergence.

The run sheet must make this interruption explicit.

### AMI lifecycle

Add a safe retirement command rather than accumulating every Packer output. It
should support dry-run and apply modes, protect every AMI referenced by SSM or a
live instance, and retain at least the current staging AMI plus one rollback
AMI.

### Remote observability

Verify that Alloy can deliver logs and telemetry to the configured Grafana
Cloud destination and that operators can query it. Local container health alone
is insufficient.

## Next execution slice

1. Implement the app-role SSM managed-channel permissions.
2. Diff and deploy Security.
3. Verify app-host SSM registration.
4. Inspect backend logs and fix the confirmed failure.
5. Correct the Caddy DNS-01 propagation configuration.
6. Correct EICE support and Packer key cleanup.
7. Build, verify, and publish a fresh AMI only for changes baked into the AMI.
8. Replace the fixed-address hosts and deploy Application exclusively.
9. Run the completion checks below.

## Completion checks

- both EC2 instances pass AWS status checks;
- both hosts are reachable through the intended management or recovery path;
- cloud-init and FlowForm bootstrap units completed without errors;
- expected containers are running and healthy;
- the backend establishes IAM-authenticated RDS connections;
- Caddy serves a valid public certificate;
- API health and readiness succeed through the public proxy;
- logs from both hosts are queryable remotely;
- no temporary build credential remains in the AMI;
- a second convergence or replacement run is repeatable.
