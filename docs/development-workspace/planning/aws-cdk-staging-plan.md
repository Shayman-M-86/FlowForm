---
title: AWS CDK staging plan
aliases: ["AWS CDK staging plan"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, configuration, ci-cd]
related_code:
  - "../../../infra/deployment/aws/cdk/"
  - "../../../infra/deployment/bootstrap/"
  - "../../../infra/containers/"
  - "../../../infra/images/"
  - "../../../.github/workflows/"
related_docs:
  - "Engineering planning"
  - "ADR 0001: AWS staging infrastructure target"
  - "AWS stack specifications"
  - "AWS staging runtime convergence"
  - "AWS staging bring-up"
---

# AWS CDK staging plan

> Staging delivery checkpoint. Detailed current work is tracked in
> [[aws-staging-runtime-convergence|AWS staging runtime convergence]].

The initial infrastructure construction phase is substantially complete.
Security, Registry, Network, Database, DatabaseBootstrap, and Application have
all been deployed to staging. The remaining immediate work is no longer stack
scaffolding; it is making the deployed proxy and application hosts converge
reliably and proving the service end to end.

## Completed foundation

| Area | Checkpoint |
| --- | --- |
| Target architecture | Recorded in ADR 0001 |
| Security and deployment identities | Deployed |
| ECR registry and digest promotion | Deployed and exercised |
| Four-subnet network | Deployed and previously verified in AWS |
| RDS PostgreSQL | Deployed as private, encrypted, single-AZ staging infrastructure |
| Database bootstrap | Baseline databases, roles, grants, and tables created and repeat-verified |
| Golden image pipeline | Doctor, build, verification, and SSM publication exercised |
| Application infrastructure | Proxy and app EC2 instances deployed |
| Proxy runtime | Caddy, Squid, and Alloy containers start successfully |

These milestones establish the infrastructure shape. They do not yet prove
that the public API or backend is healthy.

## Current execution phase

The active phase is runtime convergence:

1. Restore Systems Manager access to the private application host.
2. Inspect and correct the backend container startup failure.
3. Prove a live IAM-authenticated connection from the backend to both RDS
   databases.
4. Correct Caddy's Route 53 DNS-01 certificate timing and verify public HTTPS.
5. Make EC2 Instance Connect a tested recovery path and remove the Packer
   builder key from the finished AMI.
6. Document or automate safe replacement of fixed-private-IP hosts.

The exact blockers, order, and completion checks are kept in
[[aws-staging-runtime-convergence|AWS staging runtime convergence]] so this
checkpoint does not grow back into an implementation diary.

## Later phases

After runtime convergence:

- deploy and verify the frontend and public DNS paths;
- complete the observability stack and prove remote logs, metrics, and traces;
- finish release automation around reviewed `feature` to `staging` pull
  requests;
- implement safe AMI retirement while protecting the current and rollback
  images;
- revisit deferred image vulnerability findings before production readiness;
- run staging acceptance and update canonical Project Knowledge from live
  evidence.

## Standing constraints

- Staging remains one public proxy host, one private app host, and one private
  single-AZ RDS instance.
- RDS uses two subnets only because its subnet group must span two Availability
  Zones.
- There is no NAT Gateway, load balancer, orchestrator, RDS Proxy, or permanent
  paid VPC interface endpoint in the target.
- Private-host AWS API traffic uses the controlled Squid path, with the S3
  gateway endpoint serving S3 traffic.
- Images are promoted by digest and the AMI ID is published through SSM before
  Application deployment.
- Secrets are not baked into images or committed to source.
- The current fixed private addresses mean an EC2 replacement cannot use
  CloudFormation's normal create-before-delete sequence. Until that design is
  changed, replacement is an explicit operator operation.

## Completion boundary

This plan can be archived after staging has:

- healthy proxy and backend containers after a clean host replacement;
- working app-host SSM and recovery access;
- valid public TLS and a healthy API response;
- verified IAM database connections;
- usable remote operational telemetry;
- a repeatable reviewed deployment path from the exact merged staging commit.
