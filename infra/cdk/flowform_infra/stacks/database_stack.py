from aws_cdk import Stack
from aws_cdk import aws_kms as kms
from constructs import Construct

from flowform_infra.config import EnvConfig
from flowform_infra.stacks.network_stack import NetworkStack


class DatabaseStack(Stack):
    """RDS PostgreSQL for the core/response database split.

    TODO: build out
      - one aws_rds.DatabaseInstance per DB (core, response) or one
        instance hosting both databases, mirroring the existing
        infra/postgres/init split — decide based on cost vs isolation
      - subnet group from network_stack's private subnets
      - security group allowing ingress only from the ECS service SG
      - env_config.deletion_protection / env_config.removal_policy wired
        through; env_config.db_instance_class for sizing
      - encryption at rest using the security_stack KMS key
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_config: EnvConfig,
        network_stack: NetworkStack,
        kms_key: kms.Key,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_config = env_config
        self.network_stack = network_stack
        self.kms_key = kms_key
