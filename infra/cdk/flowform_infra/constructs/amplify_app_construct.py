from aws_cdk import SecretValue
from aws_cdk import aws_amplify as amplify_cfn
from aws_cdk import aws_amplify_alpha as amplify_alpha
from aws_cdk import aws_codebuild as codebuild
from constructs import Construct

from flowform_infra.config import EnvConfig


class AppAmplifyApp(Construct):
    """An Amplify Hosting app with a single env-specific branch, connected to GitHub.

    The repo connection uses the Amplify **GitHub App** flow (the app is
    already installed on the repository — that's how the original
    hand-made public-site app is connected): a GitHub PAT, read from
    Secrets Manager, is supplied at app creation via the CFN `AccessToken`
    property, after which webhooks and repo access run through the
    installed GitHub App rather than the token. The L2 construct only
    knows the legacy OAuth flow (`OauthToken`), so the property is
    remapped via an escape hatch below. The PAT secret must exist before
    deploy — see docs/manual-prerequisites.md.

    Each app gets a plain, single-app `build_spec` (no `applications:`/
    `appRoot` monorepo format) even though this is a pnpm workspace. Each
    Amplify App here only ever builds one frontend, so monorepo app-root
    matching adds nothing: the build_spec just `cd`s into the workspace
    root and runs a pnpm filter script.

    IMPORTANT: an `amplify.yml` (and `customHttp.yml`) committed at the
    repo root takes precedence over anything set on the App resource —
    Amplify silently ignores this construct's build_spec and headers if
    those files exist on the built branch. They were removed from the repo
    for exactly that reason; don't reintroduce them.
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
        custom_rules: list[amplify_alpha.CustomRule] | None = None,
        environment_variables: dict[str, str] | None = None,
        domain_name: str | None = None,
        extra_sub_domain_prefixes: tuple[str, ...] = (),
        github_owner: str | None = None,
        github_repository: str | None = None,
        github_token_secret_name: str | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        source_code_provider = None
        github_token: SecretValue | None = None
        if github_owner is not None:
            assert github_repository is not None and github_token_secret_name is not None
            github_token = SecretValue.secrets_manager(github_token_secret_name)
            source_code_provider = amplify_alpha.GitHubSourceCodeProvider(
                owner=github_owner,
                repository=github_repository,
                oauth_token=github_token,
            )

        # AMPLIFY_DIFF_DEPLOY=false is set on every app for two reasons:
        # skip-unchanged-build heuristics aren't wanted here, and it keeps
        # the EnvironmentVariables template property non-empty. If the
        # property is omitted (empty dict), CloudFormation leaves whatever
        # env vars the live app already has instead of clearing them —
        # stale values then survive deploys (observed: a leftover
        # AMPLIFY_MONOREPO_APP_ROOT kept forcing monorepo build mode).
        self.app = amplify_alpha.App(
            self,
            "App",
            app_name=f"flowform-{env_config.env_name}-{app_name}",
            source_code_provider=source_code_provider,
            build_spec=codebuild.BuildSpec.from_object_to_yaml(build_spec),
            custom_response_headers=custom_response_headers,
            custom_rules=custom_rules,
            environment_variables={
                "AMPLIFY_DIFF_DEPLOY": "false",
                **(environment_variables or {}),
            },
        )

        # The L2 provider only emits the legacy `OauthToken` property, but
        # the GitHub App flow expects the PAT in `AccessToken` — remap it.
        # unsafe_unwrap() is safe here: the value is a
        # {{resolve:secretsmanager:...}} dynamic reference resolved by
        # CloudFormation at deploy, never a plaintext secret in the
        # template — it's only needed because property overrides aren't
        # marked as SecretValue-accepting, tripping checkSecretUsage.
        if github_token is not None:
            cfn_app = self.app.node.default_child
            assert isinstance(cfn_app, amplify_cfn.CfnApp)
            cfn_app.add_property_override("AccessToken", github_token.unsafe_unwrap())
            cfn_app.add_property_deletion_override("OauthToken")

        if not env_config.full_deployment:
            raise ValueError(f"Amplify apps are only configured for full deployments, got '{env_config.env_name}'")
        branch = "main" if env_config.env_name == "prod" else env_config.env_name
        self.branch = self.app.add_branch(branch)

        # Domain association. The hosted zone lives in Route 53 in this
        # same account, so Amplify creates the DNS records and the ACM
        # validation records itself — no manual DNS step. Root prefix ""
        # maps domain_name itself; extra prefixes (e.g. "www") ride on it.
        self.domain = None
        if domain_name is not None:
            self.domain = self.app.add_domain(
                "Domain",
                domain_name=domain_name,
                sub_domains=[
                    amplify_alpha.SubDomain(branch=self.branch, prefix=prefix)
                    for prefix in ("", *extra_sub_domain_prefixes)
                ],
            )
