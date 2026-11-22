# Incident response

**Status: Runbook framework; environment-specific commands are not yet verified.**

1. Establish impact, affected environment and incident owner.
2. Preserve relevant logs and audit evidence without redistributing secrets.
3. Contain affected credentials, endpoints or workloads.
4. Restore service through a tested recovery or rollback path.
5. Verify service health, permissions and data integrity.
6. Record the timeline, root cause and corrective actions.

Exposed credentials require revocation or rotation. Deleting a credential from Git history or logs does not invalidate it.
