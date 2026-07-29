"""Shared runtime parameter-name contract for AWS and Proxmox deployments."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract_path = Path(__file__).resolve().parents[5] / "contracts" / "runtime-parameters.json"
    with contract_path.open(encoding="utf-8") as contract_file:
        contract: dict[str, Any] = json.load(contract_file)
    if contract.get("schema_version") != 1:
        raise ValueError(f"unsupported runtime parameter contract: {contract_path}")
    return contract


def scope_parameter_name(scope_name: str, logical_name: str) -> str:
    """Return the canonical scoped SSM parameter name."""
    suffix = _contract()["scope_parameters"][logical_name]
    return f"/flowform/{scope_name}/{suffix}"


def runtime_group_path(scope_name: str, group: str) -> str:
    """Return the SSM path prefix a runtime group is published under."""
    path = _contract()["runtime_groups"][group]["path"]
    return f"/flowform/{scope_name}/{path}"


def runtime_parameter_name(scope_name: str, group: str, logical_name: str) -> str:
    """Return the full SSM parameter name for one runtime-group parameter.

    The last path segment is the environment-variable name the backend expects,
    because bootstrap renders each parameter under the group path directly into
    `KEY=value` lines.
    """
    parameters = _contract()["runtime_groups"][group]["parameters"]
    env_name = parameters[logical_name]["name"]
    return f"{runtime_group_path(scope_name, group)}/{env_name}"


def runtime_group_logical_names(group: str) -> frozenset[str]:
    """Return every logical parameter name declared for a runtime group."""
    return frozenset(_contract()["runtime_groups"][group]["parameters"])
