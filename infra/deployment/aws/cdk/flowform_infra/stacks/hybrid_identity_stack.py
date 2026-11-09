from typing import Literal

from aws_cdk import ArnFormat, CfnOutput, Stack
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rolesanywhere as rolesanywhere
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.config.deployment_contract import release_parameter_name
from flowform_infra.stacks.registry_stack import RegistryStack
from flowform_infra.stacks.security_stack import SecurityStack

HybridRole = Literal["proxy", "app"]


class HybridIdentityStack(Stack):
    """IAM Roles Anywhere identities for the Proxmox hybrid proxy and app hosts.

    The hybrid hosts run the same bootstraps and containers as the EC2 hosts;
    only their AWS identity differs. A private CA (created by
    infra/deployment/hybrid/scripts/identity) is the trust anchor, and each
    host certificate's CN selects exactly one role. The stack is separate from
    the EC2 Proxy and App stacks so it survives their teardown.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        security_stack: SecurityStack,
        registry_stack: RegistryStack,
        ca_certificate_pem: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        env_name = env_config.env_name
        scope_name = env_config.security_scope

        self.trust_anchor = rolesanywhere.CfnTrustAnchor(
            self,
            "TrustAnchor",
            name=f"flowform-{env_name}-hybrid",
            enabled=True,
            source=rolesanywhere.CfnTrustAnchor.SourceProperty(
                source_type="CERTIFICATE_BUNDLE",
                source_data=rolesanywhere.CfnTrustAnchor.SourceDataProperty(
                    x509_certificate_data=ca_certificate_pem,
                ),
            ),
        )

        # Proxy: the EC2 proxy role's runtime reads, without its Route 53 ACME
        # permissions (Cloudflare terminates public TLS), plus the tunnel token
        # and the mirrored cloudflared image.
        self.proxy_role = self._role("proxy")
        self.proxy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParametersByPath"],
                resources=[self._parameter_arn(f"flowform/{scope_name}/proxy/*")],
            )
        )
        self.proxy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue"],
                resources=[
                    security_stack.observability_secret.secret_arn,
                    security_stack.tunnel_secret.secret_arn,
                ],
            )
        )
        self.proxy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Decrypt"],
                resources=[security_stack.kms_key.key_arn],
                conditions={"StringEquals": {"kms:ViaService": f"secretsmanager.{env_config.region}.amazonaws.com"}},
            )
        )
        self._grant_release_read(self.proxy_role, "proxy")
        self._grant_ecr_pull(
            self.proxy_role,
            [
                registry_stack.caddy_repository,
                registry_stack.squid_repository,
                registry_stack.alloy_repository,
                registry_stack.cloudflared_repository,
            ],
        )

        # App: the same permissions SecurityStack gives AppTaskRole (the EC2
        # app instance role). Secret.grant_read and Key.grant_encrypt_decrypt
        # would also edit the shared key policy in the Security stack, so the
        # equivalent actions are stated on this role instead.
        self.app_role = self._role("app")
        self.app_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue"],
                resources=[
                    security_stack.app_secrets.secret_arn,
                    security_stack.db_secrets.secret_arn,
                    security_stack.linkage_secret.secret_arn,
                ],
            )
        )
        self.app_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Decrypt", "kms:Encrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*"],
                resources=[security_stack.kms_key.key_arn],
            )
        )
        security_stack.email_identity.grant_send(self.app_role)
        self.app_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
                resources=[
                    self._parameter_arn(f"flowform/{scope_name}/*"),
                    self._parameter_arn(f"flowform/{env_name}/*"),
                ],
            )
        )
        self._grant_ecr_pull(
            self.app_role,
            [registry_stack.backend_repository, registry_stack.alloy_repository],
        )

        for role_name, role in (("proxy", self.proxy_role), ("app", self.app_role)):
            profile = rolesanywhere.CfnProfile(
                self,
                f"{role_name.capitalize()}Profile",
                name=f"flowform-{env_name}-hybrid-{role_name}",
                enabled=True,
                role_arns=[role.role_arn],
                duration_seconds=3600,
            )
            CfnOutput(self, f"{role_name.capitalize()}ProfileArn", value=profile.attr_profile_arn)
            CfnOutput(self, f"{role_name.capitalize()}RoleArn", value=role.role_arn)
        CfnOutput(self, "TrustAnchorArn", value=self.trust_anchor.attr_trust_anchor_arn)

    def _role(self, host_role: HybridRole) -> iam.Role:
        """Create a role assumable only through this trust anchor by one host CN."""
        conditions = {
            "ArnEquals": {"aws:SourceArn": self.trust_anchor.attr_trust_anchor_arn},
            "StringEquals": {"aws:PrincipalTag/x509Subject/CN": f"flowform-hybrid-{host_role}"},
        }
        principal = iam.ServicePrincipal("rolesanywhere.amazonaws.com")
        role = iam.Role(
            self,
            f"{host_role.capitalize()}Role",
            assumed_by=iam.PrincipalWithConditions(principal, conditions),
            description=f"FlowForm {self.env_config.env_name} hybrid {host_role} host (IAM Roles Anywhere)",
        )
        assume_role_policy = role.assume_role_policy
        assert assume_role_policy is not None
        # Roles Anywhere also tags the session and sets its source identity.
        assume_role_policy.add_statements(
            iam.PolicyStatement(
                actions=["sts:TagSession", "sts:SetSourceIdentity"],
                principals=[principal],
                conditions=conditions,
            )
        )
        return role

    def _parameter_arn(self, resource_name: str) -> str:
        return self.format_arn(
            service="ssm",
            resource="parameter",
            resource_name=resource_name,
            arn_format=ArnFormat.SLASH_RESOURCE_NAME,
        )

    def _grant_release_read(self, role: iam.Role, host_role: HybridRole) -> None:
        parameter_name = release_parameter_name(self.env_config.env_name, host_role)
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[self._parameter_arn(parameter_name.removeprefix("/"))],
            )
        )

    @staticmethod
    def _grant_ecr_pull(role: iam.Role, repositories: list[ecr.IRepository]) -> None:
        role.add_to_policy(iam.PolicyStatement(actions=["ecr:GetAuthorizationToken"], resources=["*"]))
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                resources=[repository.repository_arn for repository in repositories],
            )
        )
