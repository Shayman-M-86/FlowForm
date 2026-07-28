#!/usr/bin/env python3
"""Validate the shared Codex/Claude documentation-context setup.

This validator intentionally uses only the Python standard library so it works
in the same dependency-free environments as Docsys and CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]
SKILL_NAME = "flowform-doc-context"
VERIFICATION_SKILL_NAME = "flowform-doc-verification"
AGENT_NAME = "docs-maintainer"


def _front_matter(path: Path) -> dict[str, str]:
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
    return values


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate() -> list[str]:
    errors: list[str] = []
    codex_skill_path = (
        ROOT / ".agents" / "skills" / SKILL_NAME / "SKILL.md"
    )
    claude_skill_path = (
        ROOT / ".claude" / "skills" / SKILL_NAME / "SKILL.md"
    )

    for path in (codex_skill_path, claude_skill_path):
        _require(
            path.is_file(),
            f"missing skill: {path.relative_to(ROOT)}",
            errors,
        )
    if errors:
        return errors

    codex_skill = codex_skill_path.read_text()
    claude_skill = claude_skill_path.read_text()
    _require(
        codex_skill == claude_skill,
        "Codex and Claude flowform-doc-context skills differ",
        errors,
    )
    try:
        metadata = _front_matter(codex_skill_path)
    except ValueError as exc:
        errors.append(str(exc))
        metadata = {}
    _require(
        metadata.get("name") == SKILL_NAME,
        f"skill name must be {SKILL_NAME!r}",
        errors,
    )
    _require(
        bool(metadata.get("description")),
        "skill description must not be empty",
        errors,
    )
    _require(
        set(metadata) == {"name", "description"},
        "shared skill front matter must contain only name and description",
        errors,
    )

    verification_codex_path = (
        ROOT / ".agents" / "skills" / VERIFICATION_SKILL_NAME / "SKILL.md"
    )
    verification_claude_path = (
        ROOT / ".claude" / "skills" / VERIFICATION_SKILL_NAME / "SKILL.md"
    )
    for path in (verification_codex_path, verification_claude_path):
        _require(
            path.is_file(),
            f"missing skill: {path.relative_to(ROOT)}",
            errors,
        )
    if verification_codex_path.is_file() and verification_claude_path.is_file():
        _require(
            verification_codex_path.read_text()
            == verification_claude_path.read_text(),
            "Codex and Claude flowform-doc-verification skills differ",
            errors,
        )
        try:
            verification_metadata = _front_matter(verification_codex_path)
        except ValueError as exc:
            errors.append(str(exc))
            verification_metadata = {}
        _require(
            verification_metadata.get("name") == VERIFICATION_SKILL_NAME,
            f"skill name must be {VERIFICATION_SKILL_NAME!r}",
            errors,
        )
        _require(
            set(verification_metadata) == {"name", "description"},
            "verification skill front matter must contain only name and description",
            errors,
        )

    openai_yaml_path = (
        ROOT / ".agents" / "skills" / SKILL_NAME / "agents" / "openai.yaml"
    )
    _require(openai_yaml_path.is_file(), "missing Codex openai.yaml", errors)
    if openai_yaml_path.is_file():
        openai_yaml = openai_yaml_path.read_text()
        for expected in (
            "display_name:",
            "short_description:",
            f"${SKILL_NAME}",
            'value: "flowform-docs"',
        ):
            _require(
                expected in openai_yaml,
                f"Codex openai.yaml missing {expected!r}",
                errors,
            )

    verification_openai_yaml = (
        ROOT
        / ".agents"
        / "skills"
        / VERIFICATION_SKILL_NAME
        / "agents"
        / "openai.yaml"
    )
    _require(
        verification_openai_yaml.is_file(),
        "missing verification-skill openai.yaml",
        errors,
    )
    if verification_openai_yaml.is_file():
        openai_yaml = verification_openai_yaml.read_text()
        for expected in (
            "display_name:",
            "short_description:",
            f"${VERIFICATION_SKILL_NAME}",
            'value: "flowform-docs"',
        ):
            _require(
                expected in openai_yaml,
                f"verification openai.yaml missing {expected!r}",
                errors,
            )

    codex_agent_path = ROOT / ".codex" / "agents" / f"{AGENT_NAME}.toml"
    claude_agent_path = ROOT / ".claude" / "agents" / f"{AGENT_NAME}.md"
    _require(codex_agent_path.is_file(), "missing Codex docs-maintainer", errors)
    _require(claude_agent_path.is_file(), "missing Claude docs-maintainer", errors)

    if codex_agent_path.is_file():
        try:
            codex_agent = tomllib.loads(codex_agent_path.read_text())
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"invalid Codex agent TOML: {exc}")
            codex_agent = {}
        for key in ("name", "description", "developer_instructions"):
            _require(
                bool(codex_agent.get(key)),
                f"Codex docs-maintainer missing {key}",
                errors,
            )
        _require(
            codex_agent.get("name") == AGENT_NAME,
            f"Codex agent name must be {AGENT_NAME!r}",
            errors,
        )
        _require(
            codex_agent.get("model") == "gpt-5.6-terra",
            "Codex docs-maintainer must use gpt-5.6-terra",
            errors,
        )

    if claude_agent_path.is_file():
        try:
            claude_metadata = _front_matter(claude_agent_path)
        except ValueError as exc:
            errors.append(str(exc))
            claude_metadata = {}
        _require(
            claude_metadata.get("name") == AGENT_NAME,
            f"Claude agent name must be {AGENT_NAME!r}",
            errors,
        )
        claude_agent = claude_agent_path.read_text()
        _require(
            "model: sonnet" in claude_agent,
            "Claude docs-maintainer must use Sonnet",
            errors,
        )
        _require(
            f"- {SKILL_NAME}" in claude_agent,
            "Claude docs-maintainer must preload flowform-doc-context",
            errors,
        )

    try:
        codex_config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
        codex_hooks = json.loads((ROOT / ".codex/hooks.json").read_text())
        claude_mcp = json.loads((ROOT / ".mcp.json").read_text())
        claude_settings = json.loads((ROOT / ".claude/settings.json").read_text())
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"invalid agent configuration: {exc}")
        return errors

    codex_docs_mcp = codex_config.get("mcp_servers", {}).get("flowform-docs", {})
    claude_docs_mcp = claude_mcp.get("mcpServers", {}).get("flowform-docs", {})
    _require(bool(codex_docs_mcp), "Codex flowform-docs MCP is missing", errors)
    _require(bool(claude_docs_mcp), "Claude flowform-docs MCP is missing", errors)
    _require(
        codex_docs_mcp.get("command") == claude_docs_mcp.get("command")
        and codex_docs_mcp.get("args") == claude_docs_mcp.get("args"),
        "Codex and Claude flowform-docs MCP launchers differ",
        errors,
    )
    allowed = claude_settings.get("permissions", {}).get("allow", [])
    _require(
        "mcp__flowform-docs__*" in allowed,
        "Claude does not allow the read-only flowform-docs MCP tools",
        errors,
    )

    codex_hook_map = codex_hooks.get("hooks", {})
    claude_hook_map = claude_settings.get("hooks", {})
    _require(
        codex_hook_map == claude_hook_map,
        "Codex and Claude hook configurations differ",
        errors,
    )
    hook_commands = [
        hook.get("command", "")
        for groups in codex_hook_map.values()
        for group in groups
        for hook in group.get("hooks", [])
    ]
    _require(
        len(hook_commands) == 2,
        "Codex and Claude must share exactly two configured hooks",
        errors,
    )
    _require(
        all("tools/docs/hooks/" in command for command in hook_commands),
        "all agent hooks must use tools/docs/hooks",
        errors,
    )
    compatibility_hooks = list((ROOT / ".claude/hooks").glob("*.py"))
    _require(
        all(
            "TARGET =" in path.read_text()
            and '"tools"' in path.read_text()
            and '"hooks"' in path.read_text()
            and "os.execv" in path.read_text()
            for path in compatibility_hooks
        ),
        ".claude/hooks may contain only forwarders to tools/docs/hooks",
        errors,
    )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "agent documentation setup valid: shared skills, documentation maintainers, "
        "matching flowform-docs MCP configuration, and shared hooks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
