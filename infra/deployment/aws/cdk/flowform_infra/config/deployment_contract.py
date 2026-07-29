"""Load the shared host and release-path contract."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

HostRole = Literal["app", "proxy"]

_CONTRACTS_ROOT = Path(__file__).resolve().parents[5] / "contracts"


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract_path = _CONTRACTS_ROOT / "runtime-hosts.json"
    with contract_path.open(encoding="utf-8") as contract_file:
        contract: dict[str, Any] = json.load(contract_file)
    if contract.get("schema_version") != 1:
        raise ValueError(f"unsupported runtime host contract: {contract_path}")
    return contract


def instance_context_path() -> str:
    """Return the absolute path of the root-owned instance context."""
    return str(_contract()["instance_context"]["path"])


def instance_context_mode() -> str:
    """Return the octal mode of the root-owned instance context."""
    return str(_contract()["instance_context"]["mode"])


def host_service_name(role: HostRole) -> str:
    """Return the baked systemd unit for a role AMI."""
    return str(_contract()["roles"][role]["service"])


def peer_context_key(role: HostRole) -> str:
    """Return the instance-context field naming a role's private peer."""
    return str(_contract()["roles"][role]["peer_context_key"])


def ami_parameter_name(environment: str, role: HostRole) -> str:
    """Return the SSM parameter containing a role AMI ID."""
    template = str(_contract()["roles"][role]["ami_parameter"])
    return template.format(environment=environment)


def release_parameter_name(environment: str, role: HostRole) -> str:
    """Return the mutable SSM pointer to one complete role release."""
    template = str(_contract()["roles"][role]["release_parameter"])
    return template.format(environment=environment)
