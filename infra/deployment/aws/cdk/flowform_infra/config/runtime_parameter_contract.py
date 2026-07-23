"""Shared runtime parameter-name contract for AWS and Proxmox deployments."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract_path = Path(__file__).resolve().parents[4] / "config" / "runtime-parameter-contract.json"
    with contract_path.open(encoding="utf-8") as contract_file:
        contract: dict[str, Any] = json.load(contract_file)
    if contract.get("schema_version") != 1:
        raise ValueError(f"unsupported runtime parameter contract: {contract_path}")
    return contract


def scope_parameter_name(scope_name: str, logical_name: str) -> str:
    """Return the canonical scoped SSM parameter name."""
    suffix = _contract()["scope_parameters"][logical_name]
    return f"/flowform/{scope_name}/{suffix}"
