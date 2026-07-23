import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk.assertions import Match, Template

from flowform_infra.config import get_env_config
from flowform_infra.stacks.registry_stack import RegistryStack


def _synth_registry_stack(env_name: str = "staging") -> Template:
    env_config = get_env_config(env_name)
    cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
    app = cdk.App()
    support = cdk.Stack(app, "Support", env=cdk_env)
    publisher_role = iam.Role(
        support,
        "ImagePublisherRole",
        assumed_by=iam.AccountRootPrincipal(),
    )
    registry_key = kms.Key(support, "RegistryKey")
    stack = RegistryStack(
        app,
        "Registry",
        env_config=env_config,
        kms_key=registry_key,
        publisher_role=publisher_role,
        env=cdk_env,
    )
    return Template.from_stack(stack)


def test_staging_registry_creates_four_hardened_repositories():
    template = _synth_registry_stack()
    template.resource_count_is("AWS::ECR::Repository", 4)

    for repository_name in (
        "flowform-staging-backend",
        "flowform-staging-caddy",
        "flowform-staging-squid",
        "flowform-staging-alloy",
    ):
        template.has_resource_properties(
            "AWS::ECR::Repository",
            {
                "RepositoryName": repository_name,
                "ImageScanningConfiguration": {"ScanOnPush": True},
                "ImageTagMutability": "IMMUTABLE",
                "EncryptionConfiguration": {
                    "EncryptionType": "KMS",
                    "KmsKey": Match.any_value(),
                },
                "EmptyOnDelete": True,
                "LifecyclePolicy": {
                    "LifecyclePolicyText": Match.serialized_json(
                        Match.object_like(
                            {
                                "rules": Match.array_with(
                                    [
                                        Match.object_like(
                                            {
                                                "rulePriority": 1,
                                                "selection": Match.object_like(
                                                    {
                                                        "tagStatus": "untagged",
                                                        "countType": "sinceImagePushed",
                                                        "countNumber": 7,
                                                    }
                                                ),
                                            }
                                        ),
                                        Match.object_like(
                                            {
                                                "rulePriority": 2,
                                                "selection": Match.object_like(
                                                    {
                                                        "tagStatus": "any",
                                                        "countType": "imageCountMoreThan",
                                                        "countNumber": 30,
                                                    }
                                                ),
                                            }
                                        ),
                                    ]
                                )
                            }
                        )
                    )
                },
            },
        )


def test_image_publisher_policy_is_limited_to_registry_repositories():
    template = _synth_registry_stack()
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Action": "ecr:GetAuthorizationToken",
                                "Resource": "*",
                            }
                        ),
                        Match.object_like(
                            {
                                "Action": [
                                    "ecr:BatchCheckLayerAvailability",
                                    "ecr:CompleteLayerUpload",
                                    "ecr:InitiateLayerUpload",
                                    "ecr:PutImage",
                                    "ecr:UploadLayerPart",
                                ],
                                "Resource": Match.array_with(
                                    [
                                        {"Fn::GetAtt": [Match.string_like_regexp("BackendRepository"), "Arn"]},
                                        {"Fn::GetAtt": [Match.string_like_regexp("CaddyRepository"), "Arn"]},
                                        {"Fn::GetAtt": [Match.string_like_regexp("SquidRepository"), "Arn"]},
                                        {"Fn::GetAtt": [Match.string_like_regexp("AlloyRepository"), "Arn"]},
                                    ]
                                ),
                            }
                        ),
                    ]
                )
            }
        },
    )
    assert "repository/flowform-staging-*" not in str(template.to_json())


def test_prod_registry_retains_repositories_and_more_release_images():
    rendered = _synth_registry_stack("prod").to_json()
    repositories = [
        resource
        for resource in rendered["Resources"].values()
        if resource["Type"] == "AWS::ECR::Repository"
    ]

    assert len(repositories) == 4
    for repository in repositories:
        assert repository["DeletionPolicy"] == "Retain"
        assert repository["UpdateReplacePolicy"] == "Retain"
        assert repository["Properties"]["EmptyOnDelete"] is False
        assert '"countNumber":100' in repository["Properties"]["LifecyclePolicy"]["LifecyclePolicyText"]
