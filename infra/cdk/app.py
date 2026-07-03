#!/usr/bin/env python3
import os

import aws_cdk as cdk

from flowform_infra.config import get_env_config
from flowform_infra.stacks.amplify_stack import AmplifyStack
from flowform_infra.stacks.application_stack import ApplicationStack
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.observability_stack import ObservabilityStack
from flowform_infra.stacks.security_stack import SecurityStack

app = cdk.App()

env_name = app.node.try_get_context("env") or os.environ.get("CDK_ENV", "dev")
env_config = get_env_config(env_name)

cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
name_prefix = f"FlowForm-{env_config.env_name.capitalize()}"

all_stacks: list[cdk.Stack] = []

security_stack = SecurityStack(
    app,
    f"{name_prefix}-Security",
    env_config=env_config,
    env=cdk_env,
)
all_stacks.append(security_stack)

# dev stops here: the app, both databases, and the frontends all run
# locally (infra/docker/ + Vite dev servers), so dev's AWS footprint is the
# Security stack only. staging/prod get the full compute/hosting set.
if env_config.full_deployment:
    network_stack = NetworkStack(
        app,
        f"{name_prefix}-Network",
        env_config=env_config,
        env=cdk_env,
    )

    database_stack = DatabaseStack(
        app,
        f"{name_prefix}-Database",
        env_config=env_config,
        network_stack=network_stack,
        kms_key=security_stack.kms_key,
        env=cdk_env,
    )
    database_stack.add_dependency(network_stack)
    database_stack.add_dependency(security_stack)

    application_stack = ApplicationStack(
        app,
        f"{name_prefix}-Application",
        env_config=env_config,
        network_stack=network_stack,
        task_role=security_stack.task_role,
        kms_key=security_stack.kms_key,
        env=cdk_env,
    )
    application_stack.add_dependency(network_stack)
    application_stack.add_dependency(security_stack)
    application_stack.add_dependency(database_stack)

    amplify_stack = AmplifyStack(
        app,
        f"{name_prefix}-Amplify",
        env_config=env_config,
        env=cdk_env,
    )

    observability_stack = ObservabilityStack(
        app,
        f"{name_prefix}-Observability",
        env_config=env_config,
        env=cdk_env,
    )
    observability_stack.add_dependency(application_stack)

    all_stacks += [
        network_stack,
        database_stack,
        application_stack,
        amplify_stack,
        observability_stack,
    ]

for stack in all_stacks:
    for key, value in env_config.tags.items():
        cdk.Tags.of(stack).add(key, value)

app.synth()
