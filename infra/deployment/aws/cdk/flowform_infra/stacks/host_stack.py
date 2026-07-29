import json
from collections.abc import Sequence

from aws_cdk import ArnFormat, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from constructs import Construct

from flowform_infra.config import (
    EnvConfig,
    HostRole,
    host_service_name,
    instance_context_mode,
    instance_context_path,
    peer_context_key,
    release_parameter_name,
)


def pascal_case(logical_name: str) -> str:
    """Turn a runtime-contract name into a stable CDK construct ID."""
    return "".join(part.capitalize() for part in logical_name.split("_"))


class RoleHostStack(Stack):
    """Shared CDK mechanics for one role-specific EC2 host stack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.env_config = env_config

    def build_user_data(self, role: HostRole, peer_dns_name: str) -> ec2.UserData:
        """Write non-secret instance identity and start the baked role service."""
        context = {
            "schema_version": 1,
            "environment": self.env_config.env_name,
            "role": role,
            "region": self.env_config.region,
            "parameter_root": f"/flowform/{self.env_config.env_name}",
            "configuration_root": f"/flowform/{self.env_config.security_scope}",
            peer_context_key(role): peer_dns_name,
        }
        context_path = instance_context_path()
        context_json = json.dumps(context, indent=2, sort_keys=True)
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "set -euo pipefail",
            "install -d -m 0755 /etc/flowform",
            "umask 077",
            f"cat > {context_path} <<'FLOWFORM_CONTEXT'",
            context_json,
            "FLOWFORM_CONTEXT",
            f"chown root:root {context_path}",
            f"chmod {instance_context_mode()} {context_path}",
            f"systemctl enable --now {host_service_name(role)}",
        )
        return user_data

    def role_machine_image(self, role: HostRole) -> ec2.IMachineImage:
        direct_ami_id = self.env_config.ec2_app_ami_id if role == "app" else self.env_config.ec2_proxy_ami_id
        parameter = (
            self.env_config.ec2_app_ami_ssm_parameter if role == "app" else self.env_config.ec2_proxy_ami_ssm_parameter
        )
        if direct_ami_id:
            return ec2.MachineImage.generic_linux({self.env_config.region: direct_ami_id})
        if parameter:
            return ec2.MachineImage.from_ssm_parameter(
                parameter,
                os=ec2.OperatingSystemType.LINUX,
            )
        raise ValueError(f"EnvConfig for '{self.env_config.env_name}' must provide a Packer-built {role} AMI")

    def attach_release_read_policy(
        self,
        construct_id: str,
        role: iam.IRole,
        host_role: HostRole,
    ) -> iam.Policy:
        """Grant read-only access to one role's atomic release pointer."""
        parameter_name = release_parameter_name(self.env_config.env_name, host_role)
        policy = iam.Policy(
            self,
            construct_id,
            statements=[
                iam.PolicyStatement(
                    actions=["ssm:GetParameter"],
                    resources=[
                        self.format_arn(
                            service="ssm",
                            resource="parameter",
                            resource_name=parameter_name.removeprefix("/"),
                            arn_format=ArnFormat.SLASH_RESOURCE_NAME,
                        )
                    ],
                )
            ],
        )
        policy.attach_to_role(role)
        return policy

    def attach_ecr_pull_policy(
        self,
        construct_id: str,
        role: iam.IRole,
        repositories: Sequence[ecr.IRepository],
    ) -> iam.Policy:
        """Attach exact ECR pull permissions without mutating another stack."""
        policy = iam.Policy(
            self,
            construct_id,
            statements=[
                iam.PolicyStatement(
                    actions=["ecr:GetAuthorizationToken"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer",
                    ],
                    resources=[repository.repository_arn for repository in repositories],
                ),
            ],
        )
        policy.attach_to_role(role)
        return policy

    def root_block_devices(self) -> list[ec2.BlockDevice]:
        return [
            ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(
                    self.env_config.ec2_root_volume_size_gib,
                    volume_type=ec2.EbsDeviceVolumeType.GP3,
                    encrypted=True,
                    delete_on_termination=True,
                ),
            )
        ]
