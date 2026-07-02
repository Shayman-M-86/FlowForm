from aws_cdk import Stack
from constructs import Construct

from flowform_infra.config import EnvConfig

# TODO: build out
#   - aws_logs.LogGroup(s) for the ECS service, retention driven by env
#   - aws_cloudwatch alarms: ALB 5xx rate, ECS CPU/memory, RDS connections
#   - aws_cloudwatch.Dashboard summarizing the above
#   - this stack is AWS-native monitoring only; Sentry (app errors) and
#     PostHog (product analytics) remain external services, unaffected


class ObservabilityStack(Stack):
    """CloudWatch log groups, alarms, and a dashboard for the other stacks'
    resources.
    """

    def __init__(self, scope: Construct, construct_id: str, *, env_config: EnvConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
