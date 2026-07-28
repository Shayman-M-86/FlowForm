---
title: AWS DatabaseStack staging configuration
aliases: ["AWS DatabaseStack staging configuration"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, security, configuration]
related_code:
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_bootstrap_stack.py"
  - "../../../infra/deployment/aws/scripts/bootstrap-database.sh"
  - "../../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../../infra/deployment/aws/cdk/tests/"
related_docs:
  - "Engineering planning"
  - "AWS stack specifications"
  - "AWS database roles and bootstrap design"
  - "AWS staging runtime convergence"
---

# AWS DatabaseStack staging configuration

> Completed staging design checkpoint. CDK source and live AWS remain the
> authorities for current settings.

The persistent RDS stack and separate bootstrap workflow have been implemented
and deployed. This page retains the decisions that matter for later review
without preserving the former step-by-step implementation diary.

## Staging specification

| Setting | Staging |
| --- | --- |
| Service | Amazon RDS for PostgreSQL |
| Engine | PostgreSQL 17, explicitly pinned in CDK |
| Instance class | `db.t4g.small` |
| Availability | Single-AZ; no Multi-AZ standby |
| Placement | RDS subnets in two AZs, with the instance placed in the primary staging AZ |
| Logical databases | `flowform_core` and `flowform_response` |
| Initial storage | 20 GiB encrypted GP3 |
| Storage autoscaling | Enabled, maximum 40 GiB |
| Public access | Disabled |
| IAM database authentication | Enabled |
| Master credential | RDS-managed secret |
| RDS Extended Support | Disabled |
| Performance Insights | Enabled with seven-day retention; re-evaluate if the selected AWS tier incurs additional cost |
| Enhanced Monitoring | Disabled |
| Deletion protection | Disabled for staging |
| Removal behavior | Destroy, with the recovery policy declared in CDK |
| Network ingress | PostgreSQL only from approved application and bootstrap security groups |

The second RDS subnet exists because an RDS DB subnet group must cover two
Availability Zones. It does not imply Multi-AZ operation.

## Stack boundary

`DatabaseStack` owns persistent infrastructure:

- DB subnet group;
- PostgreSQL parameter group;
- database log groups;
- RDS instance and managed master secret;
- RDS resource-ID publication;
- IAM database-connect policy tied to the runtime identities.

It does not own a long-running migration runner, a permanent Secrets Manager
interface endpoint, or a CloudFormation custom resource that can roll back the
database after an SQL failure.

`DatabaseBootstrapStack` is a separately invoked operator helper. Its script:

1. deploys the helper;
2. creates one tagged temporary Secrets Manager interface endpoint;
3. invokes the private bootstrap Lambda;
4. verifies the sanitized result;
5. removes the endpoint even when bootstrap fails.

The bootstrap is idempotent and owns initial roles, schemas, grants, and
baseline tables. Later schema evolution belongs to a separate migration
workflow.

## Production delta

The current production sizing intention remains deliberately modest:

| Setting | Production intention |
| --- | --- |
| Instance class | `db.t4g.small` unless measured load requires change |
| Initial storage | 20 GiB |
| Storage autoscaling | Maximum 50 GiB |
| Availability | Single-AZ; Multi-AZ is not assumed |
| Deletion protection | Enabled |
| Removal behavior | Retain or snapshot according to the CDK lifecycle policy |
| Backups and retention | Stronger than staging and verified before launch |
| Monitoring | Enable paid features only after an explicit cost and operations decision |

Production is not ready merely because staging uses these settings. Backup
restore, maintenance, deletion behavior, performance, and cost must be proven
before production deployment.

## Remaining checks

- prove the deployed backend connects with both IAM database identities;
- exercise backup and restore before production;
- define the independently authorized migration runner;
- confirm the final production retention and maintenance-window settings;
- revisit capacity only from observed workload rather than speculative sizing.
