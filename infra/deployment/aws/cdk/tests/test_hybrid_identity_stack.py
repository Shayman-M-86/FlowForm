import json

import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from flowform_infra.config import DOMAIN_NAME, get_env_config, get_security_scope
from flowform_infra.stacks.hybrid_identity_stack import HybridIdentityStack
from flowform_infra.stacks.registry_stack import RegistryStack
from flowform_infra.stacks.security_stack import SecurityStack

# The real CA certificate is local-only (gitignored); synth needs only a PEM string.
CA_CERTIFICATE_PEM = "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"


def _synth() -> tuple[Template, Template]:
    env_config = get_env_config("staging")
    scope_config = get_security_scope(env_config)
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)

    probe_app = cdk.App()
    probe_stack = cdk.Stack(probe_app, "ContextProbe", env=cdk_env)
    context_key = cdk.ContextProvider.get_key(
        probe_stack, provider="hosted-zone", props={"domainName": DOMAIN_NAME}
    ).key
    app = cdk.App(context={context_key: {"Id": "/hostedzone/Z1234567890ABC", "Name": f"{DOMAIN_NAME}."}})

    security = SecurityStack(app, "Security", scope_config=scope_config, env=cdk_env)
    registry = RegistryStack(
        app,
        "Registry",
        env_config=env_config,
        kms_key=security.kms_key,
        publisher_role=security.image_publisher_role,
        env=cdk_env,
    )
    hybrid = HybridIdentityStack(
        app,
        "HybridIdentity",
        env_config=env_config,
        security_stack=security,
        registry_stack=registry,
        ca_certificate_pem=CA_CERTIFICATE_PEM,
        env=cdk_env,
    )
    return Template.from_stack(hybrid), Template.from_stack(security)


def _role_policy_statements(template: Template, role_logical_prefix: str) -> list[dict]:
    statements: list[dict] = []
    for resource in template.to_json()["Resources"].values():
        if resource["Type"] != "AWS::IAM::Policy":
            continue
        roles = json.dumps(resource["Properties"]["Roles"])
        if role_logical_prefix in roles:
            statements += resource["Properties"]["PolicyDocument"]["Statement"]
    return statements


def test_trust_anchor_uses_the_committed_ca_certificate():
    template, _ = _synth()
    template.resource_count_is("AWS::RolesAnywhere::TrustAnchor", 1)
    template.has_resource_properties(
        "AWS::RolesAnywhere::TrustAnchor",
        {
            "Enabled": True,
            "Source": {
                "SourceType": "CERTIFICATE_BUNDLE",
                "SourceData": {"X509CertificateData": CA_CERTIFICATE_PEM},
            },
        },
    )
    template.resource_count_is("AWS::RolesAnywhere::Profile", 2)


def test_each_role_trusts_only_its_host_certificate_through_the_anchor():
    template, _ = _synth()
    for host_role in ("proxy", "app"):
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Action": "sts:AssumeRole",
                                    "Principal": {"Service": "rolesanywhere.amazonaws.com"},
                                    "Condition": {
                                        "ArnEquals": {"aws:SourceArn": Match.any_value()},
                                        "StringEquals": {
                                            "aws:PrincipalTag/x509Subject/CN": f"flowform-hybrid-{host_role}"
                                        },
                                    },
                                }
                            ),
                            Match.object_like(
                                {
                                    "Action": ["sts:TagSession", "sts:SetSourceIdentity"],
                                    "Condition": Match.object_like(
                                        {
                                            "StringEquals": {
                                                "aws:PrincipalTag/x509Subject/CN": f"flowform-hybrid-{host_role}"
                                            }
                                        }
                                    ),
                                }
                            ),
                        ]
                    )
                }
            },
        )


def test_proxy_reads_tunnel_secret_and_has_no_route53_access():
    template, _ = _synth()
    statements = json.dumps(_role_policy_statements(template, "ProxyRole"))
    assert "tunnel-secrets" in statements or "TunnelSecrets" in statements
    assert "route53" not in statements
    assert "CloudflaredRepository" in statements


def test_app_role_has_the_app_task_role_runtime_grants():
    template, _ = _synth()
    statements = json.dumps(_role_policy_statements(template, "AppRole"))
    for expected in ("kms:Encrypt", "ses:SendRawEmail", "secretsmanager:GetSecretValue", "BackendRepository"):
        assert expected in statements
    assert "CloudflaredRepository" not in statements


def test_security_stack_is_not_mutated_by_the_hybrid_grants():
    _, security_template = _synth()
    assert "rolesanywhere" not in json.dumps(security_template.to_json())


def test_publishes_the_arns_the_identity_script_reads():
    template, _ = _synth()
    outputs = template.to_json()["Outputs"]
    for key in ("TrustAnchorArn", "ProxyProfileArn", "ProxyRoleArn", "AppProfileArn", "AppRoleArn"):
        assert key in outputs
