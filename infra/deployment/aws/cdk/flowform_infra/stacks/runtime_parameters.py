import json

from flowform_infra.config import EnvConfig
from flowform_infra.stacks.database_stack import DatabaseStack


def backend_runtime_values(
    env_config: EnvConfig,
    *,
    kms_key_arn: str,
    linkage_secret_arn: str,
    database_host: str | None = None,
) -> dict[str, str]:
    auth0_public = env_config.auth0_public
    runtime_public = env_config.runtime_public
    assert auth0_public is not None
    assert runtime_public is not None
    assert env_config.public_site_domain is not None

    values: dict[str, str] = {
        "runtime_environment": env_config.env_name,
        "logging_json": "true",
        "logging_level": "INFO",
        "tracing_enabled": "true",
        "tracing_otlp_endpoint": "http://alloy:4317",
        "tracing_sample_ratio": "1.0",
        "tracing_service_name": "backend",
        "site_url": f"https://{env_config.studio_domain}",
        "aws_region": env_config.region,
        "kms_key_arn": kms_key_arn,
        "cors_supports_credentials": "true",
        "auth0_domain": auth0_public.domain,
        "auth0_audience": auth0_public.audience,
        "auth0_client_id": auth0_public.client_id,
        "auth0_management_domain": runtime_public.auth0_management_domain,
        "auth0_management_id": runtime_public.auth0_management_id,
        "auth0_management_validate_on_startup": "true",
        "email_from_address": runtime_public.email_from_address,
        "database_core_name": "flowform_core",
        "database_core_app_user": DatabaseStack.CORE_APP_USER,
        "database_response_name": "flowform_response",
        "database_response_app_user": DatabaseStack.RESPONSE_APP_USER,
        "linkage_secret_arn": linkage_secret_arn,
    }

    if env_config.studio_domain is not None:
        values["cors_origins"] = json.dumps(
            [f"https://{env_config.studio_domain}", f"https://{env_config.public_site_domain}"]
        )

    if database_host is not None:
        values.update(
            database_core_auth_mode="iam",
            database_response_auth_mode="iam",
            database_core_host=database_host,
            database_response_host=database_host,
        )
    return values


def proxy_runtime_values(env_config: EnvConfig) -> dict[str, str]:
    runtime_public = env_config.runtime_public
    assert runtime_public is not None
    assert env_config.api_domain is not None

    return {
        "runtime_environment": env_config.env_name,
        "api_domain": env_config.api_domain,
        "grafana_cloud_loki_url": runtime_public.grafana_cloud_loki_url,
        "grafana_cloud_loki_user": runtime_public.grafana_cloud_loki_user,
        "grafana_cloud_tempo_endpoint": runtime_public.grafana_cloud_tempo_endpoint,
        "grafana_cloud_tempo_user": runtime_public.grafana_cloud_tempo_user,
    }
