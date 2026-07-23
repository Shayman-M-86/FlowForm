#!/usr/bin/env python3
import os

import aws_cdk as cdk

from flowform_infra.config import get_env_config, get_security_scope
from flowform_infra.stacks.application_stack import ApplicationStack
from flowform_infra.stacks.database_stack import DatabaseStack
from flowform_infra.stacks.frontend_cert_stack import FrontendCertStack
from flowform_infra.stacks.frontend_stack import FrontendStack
from flowform_infra.stacks.network_stack import NetworkStack
from flowform_infra.stacks.observability_stack import ObservabilityStack
from flowform_infra.stacks.registry_stack import RegistryStack
from flowform_infra.stacks.security_stack import SecurityStack

app = cdk.App()

env_name = app.node.try_get_context("env") or os.environ.get("CDK_ENV", "dev")
env_config = get_env_config(env_name)

cdk_env = cdk.Environment(account=env_config.account, region=env_config.region)
name_prefix = f"FlowForm-{env_config.env_name.capitalize()}"

all_stacks: list[cdk.Stack] = []

# The Security stack is per SCOPE, not per env: dev and staging share
# FlowForm-Nonprod-Security (one KMS key / secret set for both — they're
# simulation envs, duplicating paid resources buys nothing). Deploying it
# from either `-c env=dev` or `-c env=staging` updates the same stack, and
# SecurityStack derives everything from scope_config so both contexts
# synthesize the identical template. It gets the scope tag, not the active
# env's tag, for the same determinism reason.
scope_config = get_security_scope(env_config)
security_stack = SecurityStack(
    app,
    f"FlowForm-{scope_config.scope_name.capitalize()}-Security",
    scope_config=scope_config,
    env=cdk_env,
)
cdk.Tags.of(security_stack).add("flowform:env", scope_config.scope_name)

# dev stops here: the app, both databases, and the frontends all run
# locally (infra/environments/development/compose/ + Vite dev servers), so dev's AWS footprint is the
# Security stack only. staging/prod get the full compute/hosting set.
if env_config.full_deployment:
    registry_stack = RegistryStack(
        app,
        f"{name_prefix}-Registry",
        env_config=env_config,
        kms_key=security_stack.kms_key,
        publisher_role=security_stack.image_publisher_role,
        env=cdk_env,
    )
    registry_stack.add_dependency(security_stack)

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
        registry_stack=registry_stack,
        task_role=security_stack.task_role,
        kms_key=security_stack.kms_key,
        hosted_zone=security_stack.email_identity.hosted_zone,
        env=cdk_env,
    )
    application_stack.add_dependency(network_stack)
    application_stack.add_dependency(registry_stack)
    application_stack.add_dependency(security_stack)
    application_stack.add_dependency(database_stack)

    # CloudFront only accepts ACM certs from us-east-1, so the cert lives
    # in its own stack there; cross_region_references wires it into the
    # frontend stack in the app region.
    frontend_cert_stack = FrontendCertStack(
        app,
        f"{name_prefix}-FrontendCert",
        env_config=env_config,
        env=cdk.Environment(account=env_config.account, region="us-east-1"),
        cross_region_references=True,
    )

    frontend_stack = FrontendStack(
        app,
        f"{name_prefix}-Frontend",
        env_config=env_config,
        certificate=frontend_cert_stack.certificate,
        deploy_role=security_stack.frontend_deploy_role,
        env=cdk_env,
        cross_region_references=True,
    )
    frontend_stack.add_dependency(frontend_cert_stack)
    frontend_stack.add_dependency(security_stack)

    observability_stack = ObservabilityStack(
        app,
        f"{name_prefix}-Observability",
        env_config=env_config,
        env=cdk_env,
    )
    observability_stack.add_dependency(application_stack)

    all_stacks += [
        registry_stack,
        network_stack,
        database_stack,
        application_stack,
        frontend_cert_stack,
        frontend_stack,
        observability_stack,
    ]

for stack in all_stacks:
    for key, value in env_config.tags.items():
        cdk.Tags.of(stack).add(key, value)

app.synth()
