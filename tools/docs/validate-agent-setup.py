#!/usr/bin/env python3
"""Validate the lightweight Codex/Claude documentation workflow."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ("flowform-doc-context", "flowform-doc-verification")
AGENT_NAME = "docs-maintainer"


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _front_matter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{path.relative_to(ROOT)}: missing YAML front matter")
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise ValueError(f"{path.relative_to(ROOT)}: unterminated front matter")
    values: dict[str, str] = {}
    for line in text[4:marker].splitlines():
        if not line or line.startswith((" ", "\t")):
            continue
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip("\"'")
    return values, text[marker + 5 :].strip()


def _commands(hook_map: dict, event: str) -> list[str]:
    return [
        hook.get("command", "")
        for group in hook_map.get(event, [])
        for hook in group.get("hooks", [])
    ]


def _validate_skills(errors: list[str]) -> None:
    for name in SKILLS:
        canonical = ROOT / ".agents" / "skills" / name / "SKILL.md"
        mirror = ROOT / ".claude" / "skills" / name / "SKILL.md"
        for path in (canonical, mirror):
            _require(path.is_file(), f"missing skill: {path.relative_to(ROOT)}", errors)
        if not canonical.is_file() or not mirror.is_file():
            continue
        _require(
            canonical.read_text() == mirror.read_text(),
            f"Claude mirror differs from .agents canonical skill: {name}",
            errors,
        )
        try:
            metadata, _ = _front_matter(canonical)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        _require(metadata.get("name") == name, f"skill name must be {name!r}", errors)
        _require(
            set(metadata) == {"name", "description"},
            f"{name} front matter must contain only name and description",
            errors,
        )

        openai_yaml = canonical.parent / "agents" / "openai.yaml"
        _require(
            openai_yaml.is_file(),
            f"missing skill metadata: {openai_yaml.relative_to(ROOT)}",
            errors,
        )
        if openai_yaml.is_file():
            text = openai_yaml.read_text()
            _require(f"${name}" in text, f"{name} metadata must reference the skill", errors)
            _require(
                "dependencies:" not in text and "flowform-docs" not in text,
                f"{name} must not preload MCP dependencies",
                errors,
            )


def _validate_maintainers(errors: list[str]) -> None:
    codex_path = ROOT / ".codex" / "agents" / f"{AGENT_NAME}.toml"
    claude_path = ROOT / ".claude" / "agents" / f"{AGENT_NAME}.md"
    _require(codex_path.is_file(), "missing Codex docs-maintainer", errors)
    _require(claude_path.is_file(), "missing Claude docs-maintainer", errors)
    if not codex_path.is_file() or not claude_path.is_file():
        return
    try:
        codex = tomllib.loads(codex_path.read_text())
        claude_metadata, claude_body = _front_matter(claude_path)
    except (tomllib.TOMLDecodeError, ValueError) as exc:
        errors.append(f"invalid docs-maintainer configuration: {exc}")
        return
    codex_body = str(codex.get("developer_instructions", "")).strip()
    _require(codex.get("name") == AGENT_NAME, "invalid Codex docs-maintainer name", errors)
    _require(
        claude_metadata.get("name") == AGENT_NAME,
        "invalid Claude docs-maintainer name",
        errors,
    )
    required = (
        "Use document paths supplied by the parent.",
        "Do not rerun documentation discovery unless the assigned task is to locate or review documentation.",
    )
    for sentence in required:
        _require(sentence in codex_body, f"Codex docs-maintainer missing: {sentence}", errors)
        _require(sentence in claude_body, f"Claude docs-maintainer missing: {sentence}", errors)
    forbidden = ("docs_root", "get_task_context", "preloaded", "skills:")
    for token in forbidden:
        _require(
            token not in codex_path.read_text() and token not in claude_path.read_text(),
            f"docs-maintainer must not force discovery through {token!r}",
            errors,
        )


def _validate_mcp(errors: list[str]) -> None:
    try:
        codex = tomllib.loads((ROOT / ".codex/config.toml").read_text())
        claude = json.loads((ROOT / ".mcp.json").read_text())
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"invalid MCP configuration: {exc}")
        return
    codex_server = codex.get("mcp_servers", {}).get("flowform-docs", {})
    claude_server = claude.get("mcpServers", {}).get("flowform-docs", {})
    _require(bool(codex_server), "Codex flowform-docs MCP is missing", errors)
    _require(bool(claude_server), "Claude flowform-docs MCP is missing", errors)
    _require(
        codex_server.get("command") == claude_server.get("command")
        and codex_server.get("args") == claude_server.get("args"),
        "Codex and Claude flowform-docs launchers differ",
        errors,
    )
    launcher = " ".join(
        [str(codex_server.get("command", ""))]
        + [str(item) for item in codex_server.get("args", [])]
    )
    _require("tools/mcp/docsys_run.sh" in launcher, "invalid Docsys launcher", errors)
    for owner, server in (("Codex", codex_server), ("Claude", claude_server)):
        for argument in server.get("args", []):
            _require(
                not Path(str(argument)).is_absolute(),
                f"{owner} flowform-docs launcher arguments must be repository-relative",
                errors,
            )

    sys.path.insert(0, str(ROOT / "tools" / "docs"))
    try:
        module = importlib.import_module("docsys.mcp_server")
        tools = module.TOOLS
    except Exception as exc:
        errors.append(f"cannot load flowform-docs tool declarations: {exc}")
        return
    _require([tool.get("name") for tool in tools] == ["find", "read"], "MCP must advertise only find and read", errors)
    _require(
        len(json.dumps(tools, separators=(",", ":")).encode()) < 2_000,
        "combined MCP tool declarations must remain below 2 KB",
        errors,
    )
    for tool in tools:
        schema = tool.get("inputSchema", {})
        _require(schema.get("additionalProperties") is False, f"{tool.get('name')} must reject unknown properties", errors)
        annotations = tool.get("annotations", {})
        _require(annotations.get("readOnlyHint") is True, f"{tool.get('name')} must be marked read-only", errors)
        _require("docs_root" not in schema.get("properties", {}), f"{tool.get('name')} must not expose docs_root", errors)
    by_name = {tool["name"]: tool for tool in tools}
    if "find" in by_name:
        limit = by_name["find"]["inputSchema"]["properties"].get("limit", {})
        _require(limit.get("maximum") == 5, "MCP find limit must be capped at 5", errors)
    if "read" in by_name:
        max_chars = by_name["read"]["inputSchema"]["properties"].get("max_chars", {})
        _require(max_chars.get("maximum") == 8_000, "MCP read max_chars must be capped at 8000", errors)


def _validate_hooks(errors: list[str]) -> None:
    try:
        codex = json.loads((ROOT / ".codex/hooks.json").read_text()).get("hooks", {})
        claude = json.loads((ROOT / ".claude/settings.json").read_text()).get("hooks", {})
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid hook configuration: {exc}")
        return
    for owner, hook_map in (("Codex", codex), ("Claude", claude)):
        session_commands = _commands(hook_map, "SessionStart")
        _require(
            not any("doc" in command.lower() for command in session_commands),
            f"{owner} must not run documentation SessionStart hooks",
            errors,
        )
    removed = (
        ROOT / "tools/docs/hooks/session_start_doc_suggestion.py",
        ROOT / "tools/docs/hooks/stop_doc_impact_review.py",
        ROOT / "tools/docs/hooks/record_doc_review.py",
        ROOT / ".claude/hooks/stop_doc_impact_review.py",
    )
    for path in removed:
        _require(not path.exists(), f"obsolete hook remains: {path.relative_to(ROOT)}", errors)


def validate() -> list[str]:
    errors: list[str] = []
    _validate_skills(errors)
    _validate_maintainers(errors)
    _validate_mcp(errors)
    _validate_hooks(errors)
    _require(
        (ROOT / "tools/docs/bin/docsys").is_file(),
        "missing tools/docs/bin/docsys",
        errors,
    )
    _require(
        (ROOT / "tools/docs/sync-agent-doc-config.py").is_file(),
        "missing documentation-agent sync command",
        errors,
    )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("agent documentation workflow valid: on-demand skills, bounded MCP, and no startup documentation hook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
