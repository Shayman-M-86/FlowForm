from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.stacks.network_stack import NetworkStack

# Decided direction: EC2 + Docker Compose + Caddy (not ECS/ALB). The
# instance runs infra/docker/docker-compose.ec2.yml with two services —
# Caddy (TLS termination + reverse proxy) and the Flask/Gunicorn backend
# image from ECR. Postgres does NOT run on the instance; both logical
# databases (core + response) live on RDS (database_stack, later
# milestone). The frontend stacks already bake
# https://api.<public_site_domain> into the SPA builds, so that hostname
# is what this stack must eventually serve.
#
# TODO: build out
#   - aws_ecr.Repository for the Flask API image (and one for the custom
#     Caddy image — stock Caddy lacks the Route 53 DNS provider, so we
#     build it with xcaddy + caddy-dns/route53)
#   - aws_ec2.Instance (small, e.g. t4g.small) in a public subnet from
#     network_stack, with an Elastic IP
#   - security group: inbound 443 (and optionally 80 for the HTTPS
#     redirect only); no SSH — access is via SSM Session Manager
#   - instance role (task_role below becomes/feeds this): Route 53
#     ChangeResourceRecordSets scoped to the hosted zone (Caddy DNS-01
#     cert validation), Secrets Manager read on app/db secrets, SSM
#     params read, ECR pull, AmazonSSMManagedInstanceCore
#   - IMDSv2 hop limit 2 so containers can reach instance credentials
#     (Caddy needs the role via IMDS; hop limit 1 blocks containerized
#     callers — verify this early in staging)
#   - user data / SSM document: install Docker + Compose plugin, fetch
#     secrets to files, docker compose up
#   - Route 53 A record api.<public_site_domain> -> Elastic IP
#   - backend deploy job in .github/workflows/deploy.yml: build/push
#     image to ECR, run migrations, then SSM SendCommand to
#     `docker compose pull && docker compose up -d` (no SSH from CI)
#
# Secrets delivery (resolved by choosing EC2): keep the existing *_FILE
# pattern from docker-compose.dev.yml. The instance bootstrap (user data /
# SSM document, re-run on every deploy) does two fetches using the
# instance role — the app containers never call Secrets Manager/SSM for
# config themselves:
#   1. Secrets Manager -> /run/flowform/secrets/<NAME>.secret.txt
#      (DB app passwords, Flask secret key, Auth0 Management API client
#      secret; tmpfs mount, root-owned 0600 — memory-backed, nothing rests
#      on EBS, gone on reboot until bootstrap re-runs). Compose mounts
#      these as file secrets at /run/secrets/..., identical to dev.
#   2. SSM get-parameters-by-path /flowform/<env>/backend/ ->
#      /opt/flowform/backend.env (non-secret FLOWFORM_* config: Auth0
#      IDs, KMS key ARN, linkage secret ARN, SES from-address, logging,
#      DB hosts/names/users). Compose is invoked with
#      `--env-file /opt/flowform/backend.env` (interpolation) and the
#      backend service also loads it via `env_file:` (container env).
# See infra/docker/docker-compose.ec2.yml for the consuming side.
#
# TODO(backend, required before EC2 works): AwsSettings in
# backend/app/core/config.py makes access_key_id/secret_access_key
# required and app/aws/client_extension.py passes them to boto3
# explicitly, which blocks instance-role credentials. Make the static
# keys optional; when absent, fall through to boto3's default credential
# chain (env -> profile -> IMDS) so EC2 uses the instance role and dev
# keeps using its keys unchanged.


class ApplicationStack(Stack):
    """EC2 instance running Caddy + Flask/Gunicorn via Docker Compose."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        task_role: iam.IRole,
        kms_key: kms.Key,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        self.network_stack = network_stack
        self.task_role = task_role
        self.kms_key = kms_key
