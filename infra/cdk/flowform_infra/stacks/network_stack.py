from aws_cdk import Stack
from constructs import Construct

from flowform_infra.config import EnvConfig


class NetworkStack(Stack):
    """VPC, subnets, security groups.

    TODO: build out
      - aws_ec2.Vpc with public + private (isolated or NAT) subnets
      - security groups for: ALB (public ingress 443), ECS service
        (ingress from ALB SG only), RDS (ingress from ECS SG only)
      - consider VPC endpoints (Secrets Manager, S3, ECR) to cut NAT costs
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        self.vpc = None  # TODO: aws_ec2.Vpc(...)
