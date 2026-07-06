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
# pattern from docker-compose.dev.yml — a bootstrap step on the instance
# fetches Secrets Manager values to files under a root-owned directory
# and the Compose file mounts them as secrets at /run/secrets/..., so
# backend/app/core/config.py needs no changes.


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
