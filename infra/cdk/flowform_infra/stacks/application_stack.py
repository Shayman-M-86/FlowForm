from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.stacks.network_stack import NetworkStack

# Decided direction: TWO EC2 instances + Docker Compose (not ECS/ALB, no
# NAT Gateway, no paid interface endpoints) — the "cheapest hardened"
# shape in docs/cost-model.md, detailed in
# docs/implementation-sketch/caddy-ec2-implementation-notes.md:
#
#   - PUBLIC proxy EC2 (public subnet, Elastic IP): Caddy terminates TLS
#     for api.<public_site_domain> and reverse proxies to the app
#     instance's PRIVATE IP; Squid is the outbound forward proxy with a
#     domain allow-list (Auth0 + the AWS service endpoints the app uses).
#   - PRIVATE app EC2 (private subnet, no public IP, NO internet route):
#     runs the Flask/Gunicorn backend via docker-compose. All external
#     traffic — including AWS API calls — rides the proxy on 3128; ECR
#     image LAYERS ride the free S3 gateway endpoint; RDS is local VPC.
#
# Postgres does NOT run on either instance; both logical databases
# (core + response) live on RDS (database_stack, later milestone).
#
# TODO: build out
#   - aws_ecr.Repository for the Flask API image, the custom Caddy image
#     (xcaddy + caddy-dns/route53 — stock Caddy lacks the provider), and
#     Squid
#   - network_stack: private app subnet with NO 0.0.0.0/0 route, free S3
#     gateway endpoint, RDS subnets — see the notes doc
#   - proxy instance (t4g.small, public subnet, EIP): SG inbound 80/443
#     from anywhere + 3128 from the app SG only; its own slim role
#     (Route 53 zone-scoped changes for DNS-01, ECR pull, SSM core)
#   - app instance (t4g.small, private subnet): SG inbound backend port
#     from proxy SG only; instance profile wraps security_stack.task_role
#     (secrets/KMS/SES/ECR)
#   - IMDSv2 hop limit 2 on BOTH instances (containers need role creds)
#   - proxy env plumbing on the app instance: HTTP(S)_PROXY for the
#     Docker daemon and the backend container; NO_PROXY must include
#     localhost,127.0.0.1,169.254.169.254 (IMDS), the VPC CIDR (RDS +
#     S3 endpoint must not hairpin), and Docker service names
#   - management path: proxy box via SSM; app box via a FREE EC2
#     Instance Connect Endpoint (Session Manager cannot traverse an
#     HTTPS proxy) — deploys run through that path or an SSM document
#     on the proxy relaying compose commands
#   - Route 53 A record api.<public_site_domain> -> proxy Elastic IP
#   - backend deploy job in .github/workflows/deploy.yml: build/push
#     image to ECR, run migrations, then restart compose on the app
#     instance via the management path (no SSH from CI)
#
# Secrets delivery (resolved): keep the existing *_FILE pattern from
# docker-compose.dev.yml. The APP instance bootstrap (user data / deploy
# command, re-run on every deploy) does two fetches using the instance
# role, with the AWS calls riding the egress proxy — the app containers
# never call Secrets Manager/SSM for config themselves:
#   1. Secrets Manager -> /run/flowform/secrets/<NAME>.secret.txt
#      (DB app passwords, Flask secret key, Auth0 Management API client
#      secret; tmpfs mount, root-owned 0600 — memory-backed, nothing rests
#      on EBS, gone on reboot until bootstrap re-runs). Compose mounts
#      these as file secrets at /run/secrets/..., identical to dev.
#   2. SSM get-parameters-by-path /flowform/<scope>/backend/ ->
#      /opt/flowform/backend.env (non-secret FLOWFORM_* config: Auth0
#      IDs, KMS key ARN, linkage secret ARN, SES from-address, logging,
#      DB hosts/names/users, image refs, private IPs, HTTP(S)_PROXY/NO_PROXY).
#      Compose is invoked with `--env-file /opt/flowform/backend.env`
#      (interpolation) and the backend service also loads it via `env_file:`
#      (container env).
# See infra/docker/docker-compose.proxy.yml and docker-compose.app.yml for the
# consuming side: the proxy instance runs Caddy+Squid, and the app instance
# runs only the backend.
#
# Backend AWS calls (boto3 SESv2/KMS/Secrets Manager) use the instance
# role via IMDS and honor HTTPS_PROXY from the environment — AwsSettings'
# static keys are already optional (dev-only).


class ApplicationStack(Stack):
    """Public proxy EC2 (Caddy+Squid) + private app EC2 (Flask/Gunicorn)."""

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
