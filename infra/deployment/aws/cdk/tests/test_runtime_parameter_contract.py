import importlib.util
import json
from pathlib import Path

from flowform_infra.config import (
    ami_parameter_name,
    host_service_name,
    instance_context_mode,
    instance_context_path,
    peer_context_key,
    release_parameter_name,
)

MODULE_PATH = Path(__file__).parents[1] / "flowform_infra/config/runtime_parameter_contract.py"
SPEC = importlib.util.spec_from_file_location("runtime_parameter_contract", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
scope_parameter_name = MODULE.scope_parameter_name

CONTRACTS_ROOT = Path(__file__).parents[4] / "contracts"


def test_scope_parameter_names_are_shared_with_rehearsal_contract():
    assert scope_parameter_name("nonprod", "kms_key_arn") == "/flowform/nonprod/kms-key-arn"
    assert scope_parameter_name("prod", "linkage_secret_arn") == "/flowform/prod/linkage-secret-arn"


def test_host_contract_declares_role_ami_and_release_parameters():
    contract = json.loads((CONTRACTS_ROOT / "runtime-hosts.json").read_text())

    assert contract["instance_context"] == {
        "path": "/etc/flowform/instance-context.json",
        "owner": "root",
        "group": "root",
        "mode": "0600",
    }
    assert contract["roles"]["app"]["ami_parameter"] == "/flowform/{environment}/ec2/appAmiId"
    assert contract["roles"]["app"]["release_parameter"] == "/flowform/{environment}/app/release"
    assert contract["roles"]["proxy"]["ami_parameter"] == "/flowform/{environment}/ec2/proxyAmiId"
    assert contract["roles"]["proxy"]["release_parameter"] == "/flowform/{environment}/proxy/release"


def test_cdk_host_helpers_read_the_canonical_contract():
    assert instance_context_path() == "/etc/flowform/instance-context.json"
    assert instance_context_mode() == "0600"
    assert host_service_name("app") == "flowform-app.service"
    assert host_service_name("proxy") == "flowform-proxy.service"
    assert peer_context_key("app") == "proxy_dns_name"
    assert peer_context_key("proxy") == "app_dns_name"
    assert ami_parameter_name("staging", "app") == "/flowform/staging/ec2/appAmiId"
    assert ami_parameter_name("staging", "proxy") == "/flowform/staging/ec2/proxyAmiId"
    assert release_parameter_name("staging", "app") == "/flowform/staging/app/release"
    assert release_parameter_name("staging", "proxy") == "/flowform/staging/proxy/release"


def test_release_schemas_require_only_role_owned_images():
    app_schema = json.loads((CONTRACTS_ROOT / "app-release.schema.json").read_text())
    proxy_schema = json.loads((CONTRACTS_ROOT / "proxy-release.schema.json").read_text())

    assert app_schema["properties"]["images"]["required"] == ["backend", "alloy"]
    assert proxy_schema["properties"]["images"]["required"] == ["caddy", "squid", "alloy"]
    assert app_schema["properties"]["images"]["additionalProperties"] is False
    assert proxy_schema["properties"]["images"]["additionalProperties"] is False
