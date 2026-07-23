---
title: Active plans
aliases:
  - "Active plans"
document_type: planning-index
status: draft
authority: planning
verified_against_commit: null
tags: [meta]
related_code: []
related_docs:
  - "Planning workspace"
---

# Active plans
Provides a tracked directory for active planning documents.

## Purpose
This directory stores work that is currently being designed or executed, keeping proposals separate from canonical documentation.

## Entry criteria
Keep a plan here only while it has unfinished decisions or implementation work. State its owner or next action when that is known.

## Current plans

- [[aws-cdk-staging-plan|AWS CDK staging plan]] — proposed low-cost staging
  architecture, delivery sequence, and acceptance gate for the AWS CDK target.

## Required content
Each plan should include purpose, scope, verified evidence, assumptions, decisions needed, validation, and exit criteria.

## Promotion rules
When work finishes, update implementation-backed canonical documents separately, create an ADR only for a supported lasting decision, then move the plan to `completed/` or `abandoned/`.

## Related documents

- [[70-planning/README|Planning workspace]]
