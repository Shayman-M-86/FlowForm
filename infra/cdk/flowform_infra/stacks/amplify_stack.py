from aws_cdk import Stack
from aws_cdk import aws_amplify_alpha as amplify_alpha
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.constructs.amplify_app_construct import AppAmplifyApp

# Shared toolchain setup for both apps — mirrors the existing root-level
# amplify.yml (currently public-site only). `cd ../..` from appRoot lands
# in the pnpm workspace root to install once and build via a workspace
# filter script, so both frontends can share one Amplify app-level
# convention without needing their own build.

_NODE_VERSION = "22.12.0"

_PREBUILD_COMMANDS = [
    f"nvm install {_NODE_VERSION}",
    f"nvm use {_NODE_VERSION}",
    "corepack enable",
    "cd ../.. && pnpm install --frozen-lockfile --store-dir .pnpm-store",
]

_CACHE_PATHS = [
    "../../.pnpm-store/**/*",
    "../../node_modules/**/*",
    "node_modules/**/*",
]


def _build_spec(build_command: str) -> dict:
    return {
        "version": 1,
        "frontend": {
            "phases": {
                "preBuild": {"commands": _PREBUILD_COMMANDS},
                "build": {"commands": [f"cd ../.. && {build_command}"]},
            },
            "artifacts": {"baseDirectory": "dist", "files": ["**/*"]},
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

# studio-app is an authenticated SPA behind Auth0 — these are all
# non-secret, client-side values (Auth0 client ID/domain are public by
# design; the API URL is just a hostname), so they're set directly here
# rather than routed through Secrets Manager/SSM.
#
# TODO: VITE_API_BASE_URL is a placeholder (localhost only works for local
# dev, not an Amplify-hosted build) — point this at the real deployed API
# once application_stack.py's ALB/service exists and has a stable URL.
_STUDIO_APP_ENV_VARS = {
    "dev": {
        "VITE_AUTH0_DOMAIN": "dev-3wccg4jx4o5wvedn.au.auth0.com",
        "VITE_AUTH0_CLIENT_ID": "NUBi0ulto1OKmJWjUeJlzJ20XjmsgEUm",
        "VITE_AUTH0_AUDIENCE": "https://flowform.auth.api",
        "VITE_API_BASE_URL": "",  # TODO: fill in once application_stack.py exists
    },
}


class AmplifyStack(Stack):
    """Amplify Hosting apps for public-site and studio-app.

    Both apps are fully CDK-managed (build spec, headers, env vars) but not
    connected to GitHub by CDK — see AppAmplifyApp's docstring for why.
    Each app needs its repository connected once by hand in the Amplify
    console after `cdk deploy`.
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.public_site = AppAmplifyApp(
            self,
            "PublicSite",
            env_config=env_config,
            app_name="public-site",
            build_spec=_build_spec("pnpm run build:site"),
            custom_response_headers=_PUBLIC_SITE_HEADERS,
        )

        self.studio_app = AppAmplifyApp(
            self,
            "StudioApp",
            env_config=env_config,
            app_name="studio-app",
            build_spec=_build_spec("pnpm run build:studio"),
            environment_variables=_STUDIO_APP_ENV_VARS.get(env_config.env_name, {}),
        )
