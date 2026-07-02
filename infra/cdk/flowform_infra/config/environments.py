from dataclasses import dataclass, field

from aws_cdk import RemovalPolicy


@dataclass(frozen=True)
class EnvConfig:
    env_name: str
    account: str
    region: str
    removal_policy: RemovalPolicy
    deletion_protection: bool
    db_instance_class: str
    tags: dict[str, str] = field(default_factory=dict)


# Region matches the KMS key / Secrets Manager secret already in use for
# dev (see infra/docker/.backend.env FLOWFORM_ENCRYPTION_* ARNs).
_DEFAULT_REGION = "ap-southeast-2"

# Route53 hosted zone + SES domain identity, already configured by hand in
# AWS (matches FLOWFORM_EMAIL_FROM_ADDRESS=no-reply@flow-form.com.au in
# infra/docker/.backend.env). Same domain across all envs for now — revisit
# if staging/prod end up on subdomains.
DOMAIN_NAME = "flow-form.com.au"

# dev account matches the one already visible in infra/docker/.backend.env's
# ARNs. staging/prod are placeholders — TODO: confirm whether staging/prod
# live in the same AWS account as dev or in separate accounts (common
# practice for blast-radius isolation) before deploying either.
_DEV_ACCOUNT = "908123139858"

_ENVIRONMENTS: dict[str, EnvConfig] = {
    "dev": EnvConfig(
        env_name="dev",
        account=_DEV_ACCOUNT,
        region=_DEFAULT_REGION,
        removal_policy=RemovalPolicy.DESTROY,
        deletion_protection=False,
        db_instance_class="db.t4g.micro",
        tags={"flowform:env": "dev"},
    ),
    "staging": EnvConfig(
        env_name="staging",
        account="TODO-staging-account-id",
        region=_DEFAULT_REGION,
        removal_policy=RemovalPolicy.DESTROY,
        deletion_protection=False,
        db_instance_class="db.t4g.small",
        tags={"flowform:env": "staging"},
    ),
    "prod": EnvConfig(
        env_name="prod",
        account="TODO-prod-account-id",
        region=_DEFAULT_REGION,
        removal_policy=RemovalPolicy.RETAIN,
        deletion_protection=True,
        db_instance_class="db.t4g.medium",
        tags={"flowform:env": "prod"},
    ),
}


def get_env_config(env_name: str) -> EnvConfig:
    try:
        return _ENVIRONMENTS[env_name]
    except KeyError:
        valid = ", ".join(sorted(_ENVIRONMENTS))
        raise ValueError(f"Unknown env '{env_name}'. Valid options: {valid}") from None
