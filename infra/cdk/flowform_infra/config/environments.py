import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from aws_cdk import RemovalPolicy

# infra/cdk — where the per-env `.env.<env>` files live (gitignored).
_CDK_ROOT = Path(__file__).resolve().parents[2]

EnvName = Literal["dev", "staging", "prod"]


@dataclass(frozen=True)
class Auth0PublicConfig:
    """Public (client-side) Auth0 values for the studio-app SPA.

    These are safe to keep in code: the SPA is a public/PKCE client, so the
    domain, client ID, and audience all ship in the built JS bundle anyway.
    The only confidential Auth0 value (the Management API client secret)
    lives in Secrets Manager, not here.
    """

    domain: str
    client_id: str
    audience: str


@dataclass(frozen=True)
class EnvConfig:
    """Per-environment deployment settings consumed by app.py and the stacks."""

    env_name: EnvName
    account: str
    region: str
    removal_policy: RemovalPolicy
    deletion_protection: bool
    # When False (dev), only the Security stack is synthesized — the app and
    # databases run locally via Docker Compose (infra/docker/), and the
    # frontends run on local Vite dev servers. Compute/hosting fields below
    # (db_instance_class, auth0_public) are unused until this is True.
    full_deployment: bool
    db_instance_class: str
    # Build-time env vars for the Amplify-hosted studio-app. None for dev
    # (no Amplify app; local frontend env files own these). For staging/prod
    # this is filled at lookup time from the gitignored `.env.<env>` file
    # (AUTH0_DOMAIN / AUTH0_CLIENT_ID / AUTH0_AUDIENCE) — see
    # get_env_config(); the Amplify stack fails synth if it's still None.
    auth0_public: Auth0PublicConfig | None = None
    # Custom domains for the Amplify apps (None = no domain association).
    # The hosted zone is in Route 53 in this same account, so Amplify
    # creates the DNS + ACM-validation records automatically.
    public_site_domain: str | None = None
    # Extra subdomain prefixes on public_site_domain beyond the root
    # (e.g. ("www",) for prod).
    public_site_extra_prefixes: tuple[str, ...] = ()
    studio_domain: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


# Region matches the KMS key / Secrets Manager secret already in use for
# dev (see infra/docker/.backend.env FLOWFORM_ENCRYPTION_* ARNs).
_DEFAULT_REGION = "ap-southeast-2"

# Route53 hosted zone + SES domain identity, already configured by hand in
# AWS (matches FLOWFORM_EMAIL_FROM_ADDRESS=no-reply@flow-form.com.au in
# infra/docker/.backend.env). Same domain across all envs for now — revisit
# if staging/prod end up on subdomains.
DOMAIN_NAME = "flow-form.com.au"

# Decision (resolved): all environments share this single AWS account —
# isolation comes from per-env resource naming (flowform/<env>/... secrets
# and params, per-env KMS keys/stacks), not account boundaries. For a solo
# developer, AWS Organizations + member accounts was judged more operational
# overhead than it's worth right now; revisit (prod in its own member
# account) if/when the project grows. The account ID matches the ARNs
# already in infra/docker/.backend.env.
_ACCOUNT = "908123139858"

_ENVIRONMENTS: dict[EnvName, EnvConfig] = {
    # dev is deliberately tiny in AWS: local Docker Compose hosts the app
    # and both databases, so the only cloud resources are the ones the
    # backend can't fake locally (KMS key, Secrets Manager entries, SES
    # send permission). No VPC, RDS, ECS, or Amplify.
    "dev": EnvConfig(
        env_name="dev",
        account=_ACCOUNT,
        region=_DEFAULT_REGION,
        removal_policy=RemovalPolicy.DESTROY,
        deletion_protection=False,
        full_deployment=False,
        db_instance_class="db.t4g.micro",  # unused while full_deployment=False
        tags={"flowform:env": "dev"},
    ),
    # staging doubles as the shared integration environment — the one
    # non-prod cloud deployment. Anything that would want a "deployed dev"
    # (Amplify branch previews, integration testing against real ECS/RDS)
    # happens here instead of in a second paid-for environment.
    "staging": EnvConfig(
        env_name="staging",
        account=_ACCOUNT,
        region=_DEFAULT_REGION,
        removal_policy=RemovalPolicy.DESTROY,
        deletion_protection=False,
        full_deployment=True,
        db_instance_class="db.t4g.small",
        auth0_public=None,  # loaded from .env.staging by get_env_config()
        public_site_domain=f"staging.{DOMAIN_NAME}",
        studio_domain=f"studio.staging.{DOMAIN_NAME}",
        tags={"flowform:env": "staging"},
    ),
    "prod": EnvConfig(
        env_name="prod",
        account=_ACCOUNT,
        region=_DEFAULT_REGION,
        removal_policy=RemovalPolicy.RETAIN,
        deletion_protection=True,
        full_deployment=True,
        db_instance_class="db.t4g.medium",
        auth0_public=None,  # loaded from .env.prod by get_env_config()
        # NOTE: the apex is currently attached to the hand-made Amplify
        # public-site app — a domain can only belong to one Amplify app at
        # a time, so the first prod deploy requires detaching it from the
        # old app first (the cutover).
        public_site_domain=DOMAIN_NAME,
        public_site_extra_prefixes=("www",),
        studio_domain=f"studio.{DOMAIN_NAME}",
        tags={"flowform:env": "prod"},
    ),
}


def _parse_env_file(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE parser — no interpolation, `#` lines are comments."""
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _load_auth0_public(env_name: str, env_dir: Path) -> Auth0PublicConfig | None:
    """Read Auth0 public config from `.env.<env>` (gitignored), if present.

    These values are public (they ship in the built JS bundle), but keeping
    them out of git means the repo carries no live tenant/client identifiers
    and each machine/CI job states its own. Returns None when the file or
    any key is missing — the Amplify stack turns that into a fail-early
    synth error for full-deployment envs.
    """
    env_file = env_dir / f".env.{env_name}"
    if not env_file.is_file():
        return None
    values = _parse_env_file(env_file)
    try:
        return Auth0PublicConfig(
            domain=values["AUTH0_DOMAIN"],
            client_id=values["AUTH0_CLIENT_ID"],
            audience=values["AUTH0_AUDIENCE"],
        )
    except KeyError:
        return None


def get_env_config(env_name: str, env_dir: Path = _CDK_ROOT) -> EnvConfig:
    try:
        config = _ENVIRONMENTS[env_name]
    except KeyError:
        valid = ", ".join(sorted(_ENVIRONMENTS))
        raise ValueError(f"Unknown env '{env_name}'. Valid options: {valid}") from None

    if config.auth0_public is None:
        auth0_public = _load_auth0_public(env_name, env_dir)
        if auth0_public is not None:
            config = dataclasses.replace(config, auth0_public=auth0_public)
    return config
