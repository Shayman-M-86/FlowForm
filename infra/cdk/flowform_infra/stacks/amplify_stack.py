from aws_cdk import Stack
from aws_cdk import aws_amplify_alpha as amplify_alpha
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.constructs.amplify_app_construct import AppAmplifyApp

# Shared toolchain setup for both apps — mirrors the existing root-level
# amplify.yml (currently public-site only). Amplify clones the repo root
# for each app (no monorepo appRoot — see AppAmplifyApp's docstring for
# why), so commands `cd` straight into the pnpm workspace root (frontend/)
# to install once and build via a workspace filter script.

_NODE_VERSION = "22.12.0"
# Matches frontend/package.json's "packageManager" field. Installed via npm
# rather than `corepack enable` — corepack currently fails on Amplify's
# build image with "Cannot find matching keyid" while verifying pnpm's
# publish signature against npm's registry (an npm signing-key rotation
# corepack doesn't recognize yet), unrelated to this app's code.
_PNPM_VERSION = "10.24.0"

_PREBUILD_COMMANDS = [
    f"nvm install {_NODE_VERSION}",
    f"nvm use {_NODE_VERSION}",
    f"npm install -g pnpm@{_PNPM_VERSION}",
    "cd frontend && pnpm install --frozen-lockfile --store-dir .pnpm-store",
]

_CACHE_PATHS = [
    "frontend/.pnpm-store/**/*",
    "frontend/node_modules/**/*",
]

# Repo connection (GitHub App flow — see AppAmplifyApp's docstring). The
# PAT secret is shared across envs (same account) and must exist before
# the first deploy: docs/manual-prerequisites.md.
_GITHUB_OWNER = "Shayman-M-86"
_GITHUB_REPOSITORY = "FlowForm"
_GITHUB_TOKEN_SECRET_NAME = "flowform/shared/github-pat"


def _build_spec(build_command: str, artifacts_base_directory: str) -> dict:
    return {
        "version": 1,
        "frontend": {
            "phases": {
                "preBuild": {"commands": _PREBUILD_COMMANDS},
                "build": {"commands": [f"cd frontend && {build_command}"]},
            },
            "artifacts": {"baseDirectory": artifacts_base_directory, "files": ["**/*"]},
            "cache": {"paths": _CACHE_PATHS},
        },
    }


# customHttp.yml (public-site only, today) — long-lived immutable caching
# for hashed/versioned assets, shorter stale-while-revalidate for images.
_PUBLIC_SITE_HEADERS = [
    amplify_alpha.CustomResponseHeader(
        pattern="/_astro/*",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    ),
    *[
        amplify_alpha.CustomResponseHeader(
            pattern=pattern,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )
        for pattern in ("**/*.woff2", "**/*.woff")
    ],
    *[
        amplify_alpha.CustomResponseHeader(
            pattern=pattern,
            headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"},
        )
        for pattern in ("**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.webp", "**/*.svg", "**/*.ico")
    ],
]

# studio-app is an authenticated SPA behind Auth0 — its build-time env vars
# are all non-secret, client-side values (Auth0 client ID/domain are public
# by design; the API URL is just a hostname), so they come straight from
# EnvConfig.auth0_public rather than Secrets Manager/SSM.
#
# TODO: VITE_API_BASE_URL is a placeholder — point this at the deployed API
# once application_stack.py's ALB/service exists and has a stable URL.
def _studio_app_env_vars(env_config: EnvConfig) -> dict[str, str]:
    if env_config.auth0_public is None:
        raise ValueError(
            f"EnvConfig for '{env_config.env_name}' has no auth0_public config — "
            f"create infra/cdk/.env.{env_config.env_name} with AUTH0_DOMAIN, "
            "AUTH0_CLIENT_ID, and AUTH0_AUDIENCE (see .env.dev.example) "
            "before deploying the Amplify stack."
        )
    return {
        "VITE_AUTH0_DOMAIN": env_config.auth0_public.domain,
        "VITE_AUTH0_CLIENT_ID": env_config.auth0_public.client_id,
        "VITE_AUTH0_AUDIENCE": env_config.auth0_public.audience,
        "VITE_API_BASE_URL": "",  # TODO: fill in once application_stack.py exists
    }


class AmplifyStack(Stack):
    """Amplify Hosting apps for public-site and studio-app.

    Only synthesized for full deployments (staging/prod) — dev's frontends
    run on local Vite dev servers, so dev has no Amplify apps (see app.py).

    Both apps are fully CDK-managed, including the GitHub repo connection
    (GitHub App flow, PAT read from Secrets Manager at deploy — see
    AppAmplifyApp's docstring). No console steps after `cdk deploy`.
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.public_site = AppAmplifyApp(
            self,
            "PublicSite",
            env_config=env_config,
            app_name="public-site",
            build_spec=_build_spec("pnpm run build:site", "apps/public-site/dist"),
            custom_response_headers=_PUBLIC_SITE_HEADERS,
            domain_name=env_config.public_site_domain,
            extra_sub_domain_prefixes=env_config.public_site_extra_prefixes,
            github_owner=_GITHUB_OWNER,
            github_repository=_GITHUB_REPOSITORY,
            github_token_secret_name=_GITHUB_TOKEN_SECRET_NAME,
        )

        # SPA rewrite: client-side routes (no file extension) must serve
        # index.html or deep links / refreshes 404. The public site is
        # static Astro pages and doesn't need it.
        self.studio_app = AppAmplifyApp(
            self,
            "StudioApp",
            env_config=env_config,
            app_name="studio-app",
            build_spec=_build_spec("pnpm run build:studio", "apps/studio-app/dist"),
            custom_rules=[amplify_alpha.CustomRule.SINGLE_PAGE_APPLICATION_REDIRECT],
            environment_variables=_studio_app_env_vars(env_config),
            domain_name=env_config.studio_domain,
            github_owner=_GITHUB_OWNER,
            github_repository=_GITHUB_REPOSITORY,
            github_token_secret_name=_GITHUB_TOKEN_SECRET_NAME,
        )
