from aws_cdk import Stack
from constructs import Construct

from flowform_infra.config import EnvConfig

# TODO: build out
#   - bring the ALREADY-EXISTING Amplify Hosting app for public-site under
#     CDK management (does not change how public-site is built or hosted —
#     just moves the AWS-side config from console-managed to code-managed)
#   - use aws_amplify_alpha.App (or the L1 aws_amplify.CfnApp if the alpha
#     construct's API is too unstable) wired to the GitHub repo
#   - build spec should mirror the existing root-level amplify.yml
#     (appRoot: frontend/apps/public-site, pnpm build:site)
#   - custom headers should mirror the existing root-level customHttp.yml
#   - map branches to environments (e.g. main -> prod, develop -> staging)


class AmplifyStack(Stack):
    """Amplify Hosting app for public-site."""

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
