from aws_cdk import aws_amplify_alpha as amplify_alpha
from aws_cdk import aws_codebuild as codebuild
from constructs import Construct

from flowform_infra.config import EnvConfig


class AppAmplifyApp(Construct):
    """An Amplify Hosting app with a single `main` branch.

    No `source_code_provider` is set here — there's no GitHub OAuth/PAT
    token anywhere in this repo to give CDK, which means the existing
    public-site Amplify app is almost certainly connected via the newer
    console-authorized GitHub App integration rather than the legacy
    token-based one the L2 construct expects. CDK creates the app and
    branch; connecting it to GitHub is a one-time manual step per app
    (Amplify console -> App settings -> connect repository) after deploy.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        app_name: str,
        build_spec: dict,
        custom_response_headers: list[amplify_alpha.CustomResponseHeader] | None = None,
        environment_variables: dict[str, str] | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        self.app = amplify_alpha.App(
            self,
            "App",
            app_name=f"flowform-{env_config.env_name}-{app_name}",
            build_spec=codebuild.BuildSpec.from_object_to_yaml(build_spec),
            custom_response_headers=custom_response_headers,
            environment_variables=environment_variables or {},
        )
        self.main_branch = self.app.add_branch("main")
