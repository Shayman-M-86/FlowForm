"""Versioned plaintext payload encode/decode for answer encryption."""

import json
from typing import Any


class PayloadDecodeError(Exception):
    """Raised when a plaintext payload cannot be decoded."""


def build_plaintext_payload(
    payload_version: int,
    question_node_id: str,
    answer_state: str,
    answer_value: Any | None,
) -> bytes:
    """Encode a versioned plaintext payload for encryption."""
    payload = {
        "v": payload_version,
        "question_node_id": question_node_id,
        "answer_state": answer_state,
        "answer_value": answer_value,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def parse_plaintext_payload(raw: bytes) -> dict[str, Any]:
    """Decode a versioned plaintext payload after decryption."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PayloadDecodeError("Invalid payload bytes") from exc

    required_keys = {"v", "question_node_id", "answer_state", "answer_value"}
    missing = required_keys - set(data.keys())
    if missing:
        raise PayloadDecodeError(f"Missing payload fields: {sorted(missing)}")

    return {
        "payload_version": data["v"],
        "question_node_id": data["question_node_id"],
        "answer_state": data["answer_state"],
        "answer_value": data["answer_value"],
    }
