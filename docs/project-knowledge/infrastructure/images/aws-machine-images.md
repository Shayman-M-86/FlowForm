---
title: AWS machine images
aliases: ["AWS machine images", "AWS AMI lineage", "FlowForm AMIs"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:d9e7163d2b59d5a6c085f429581b68d73a781c3dd46d179e5774f6dce80f4e83
last_edited: 2026-08-04
tags: [infrastructure]
related_code:
  - "../../../../infra/machine-images/definitions/base/build.pkr.hcl"
  - "../../../../infra/machine-images/definitions/app/build.pkr.hcl"
  - "../../../../infra/machine-images/definitions/proxy/build.pkr.hcl"
  - "../../../../infra/machine-images/packer/sources/aws.pkr.hcl"
  - "../../../../infra/machine-images/tooling/lib/cmd_publish.sh"
  - "../../../../infra/machine-images/tooling/lib/cmd_prune.sh"
  - "../../../../infra/contracts/runtime-hosts.json"
change_triggers:
  - "../../../../infra/machine-images/"
  - "../../../../infra/deployment/aws/"
  - "../../../../infra/contracts/runtime-hosts.json"
related_docs: ["Machine images", "Container runtime", "Deployment architecture", "Configuration and secrets"]
---

# AWS machine images

AWS hosts use a three-artifact lineage: a non-deployable FlowForm base AMI and
separate application and proxy AMIs built from that exact base. The base is a
controlled host-capability dependency; deployment selects only a verified role
AMI.

```text
official minimal Amazon Linux 2023 AMI
                  |
                  v
          FlowForm base AMI
             /          \
            v            v
 application AMI      proxy AMI
            |            |
            +-----+------+
                  v
       environment-specific selection
```

## Lineage and role isolation

The base build starts from the configured official minimal Amazon Linux 2023
source. It installs shared host capability and AWS guest integration, including
the container runtime and management agents, but no role service or runtime
topology. Application and proxy builds resolve one exact completed base
artifact and record its identity as their parent.

Each child receives the shared host helpers plus only its own bootstrap,
systemd unit, and Compose definition. Verification rejects application assets
from the proxy image, proxy assets from the application image, and role assets
from the base. Container layers, environment secrets, endpoint values, and the
currently selected release remain runtime concerns.

The AWS builder requires instance metadata service version 2 for the temporary
build host, uses SSM for Packer communication, encrypts the root volume, and
removes temporary SSH authorization before finalizing the artifact. These are
image-build controls, not evidence about the network or health of a deployed
environment.

## Manifests and identity

Every completed build writes artifact metadata. The base manifest identifies
the AMI, role, source revision, region, architecture, and root snapshot. A role
manifest additionally records the exact parent base AMI. Equivalent ownership,
role, source, and parent data is attached as AWS tags so verification and
retention can reconstruct the lineage.

A built AMI is not automatically selected for deployment. Publication first
verifies the artifact and confirms that the active AWS identity matches the
account declared by the deployment configuration. It then writes the role AMI
identity to the environment-specific parameter consumed by deployment:

| Role | Selection parameter suffix | Publishable |
| --- | --- | --- |
| Application | `ec2/appAmiId` | Yes |
| Proxy | `ec2/proxyAmiId` | Yes |
| Base | Transitional `ec2/baseAmiId` reference only | No |

The base parameter remains readable because older or shared environment state
may still protect a base artifact. It is not a valid deployment selection and
the publication command refuses the base role.

## Retention safeguards

AMI pruning is an account-and-region operation, so protection is broader than
the one environment named at invocation. The tooling protects:

- application, proxy, and transitional base parameter values in development,
  staging, and production;
- AMIs referenced by non-terminated EC2 instances;
- the two newest application builds and two newest proxy builds; and
- the exact base parent of every protected child AMI.

Only available, self-owned images tagged as FlowForm artifacts managed by
Packer are candidates. Dry-run reports eligibility without changing AWS. Apply
deregisters only unprotected candidates and requests deletion of their
unshared associated snapshots.

These rules protect known repository-managed references. They do not discover
an undocumented external consumer, prove that an AMI boots successfully, or
replace environment verification after deployment.

## Relationship to deployment

Deployment resolves the selected application and proxy AMI identities but owns
the EC2 topology, instance context, access controls, and runtime configuration.
At boot, the baked role service reads the instance context and release manifest
and converges the role's containers. This keeps host lineage, environment
selection, and mutable service release selection as separate decisions.

## Related documents

- [[images-index|Machine images]]
- [[containers-index|Container runtime]]
- [[deployment-index|Deployment architecture]]
- [[configuration|Configuration and secrets]]
