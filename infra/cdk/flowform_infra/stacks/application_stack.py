from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.stacks.network_stack import NetworkStack

# TODO: build out
#   - aws_ecr.Repository (or reference an existing one) for the Flask API image
#   - aws_ecs.FargateService + TaskDefinition using security_stack.task_role
#   - env vars sourced from SSM params, secrets sourced from Secrets Manager
#     (task_role already has grant_read on the relevant secrets)
#   - aws_elasticloadbalancingv2.ApplicationLoadBalancer with HTTPS listener
#   - health check against the Flask API's health endpoint
#   - autoscaling policy (later, not this milestone)


class ApplicationStack(Stack):
    """ECS/Fargate service + ALB running the Flask API."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        task_role: iam.IRole,
        kms_key: kms.Key,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        self.network_stack = network_stack
        self.task_role = task_role
        self.kms_key = kms_key
