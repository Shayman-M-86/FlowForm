#!/usr/bin/env python3
"""Validate the shared, command-first Codex/Claude documentation workflow."""

from __future__ import annotations

import ast
import importlib
import json
import sys
from pathlib import Path

import tomllib

from flowform_tools.paths import ROOT

SKILLS = ("flowform-doc-context", "flowform-doc-verification")
BARE_DOCSYS_MODULES = (
    "tools/flowform_tools/docsys/core/model.py",
    "tools/flowform_tools/docsys/core/gitutil.py",
    "tools/flowform_tools/docsys/core/markdown_ast.py",
    "tools/flowform_tools/docsys/core/cli.py",
    "tools/flowform_tools/docsys/commands/validate.py",
    "tools/flowform_tools/docsys/commands/evidence.py",
    "tools/flowform_tools/docsys/commands/impact.py",
    "tools/flowform_tools/docsys/commands/debt.py",
)


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _skill_front_matter(path: Path) -> dict[str, str]:
    """Parse the deliberately narrower flat scalar metadata used by skills."""
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


def _section(path: Path, heading: str) -> str:
    text = path.read_text()
    start = text.index(f"{heading}\n")
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def _hook_commands(hook_map: dict) -> list[str]:
    return [
        hook.get("command", "")
        for groups in hook_map.values()
        for group in groups
        for hook in group.get("hooks", [])
    ]


def _validate_skills(errors: list[str]) -> None:
    for name in SKILLS:
        canonical = ROOT / ".agents" / "skills" / name / "SKILL.md"
        mirror = ROOT / ".claude" / "skills" / name / "SKILL.md"
        _require(canonical.is_file(), f"missing canonical skill: {name}", errors)
        _require(mirror.is_file(), f"missing Claude skill mirror: {name}", errors)
        if not canonical.is_file() or not mirror.is_file():
            continue
        _require(
            canonical.read_text() == mirror.read_text(),
            f"Claude skill mirror differs: {name}",
            errors,
        )
        try:
            metadata = _skill_front_matter(canonical)
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
        _require(openai_yaml.is_file(), f"missing skill metadata: {name}", errors)
        if openai_yaml.is_file():
            metadata_text = openai_yaml.read_text().casefold()
            _require(f"${name}" in metadata_text, f"{name} metadata is stale", errors)
            _require(
                "dependencies:" not in metadata_text and "mcp" not in metadata_text,
                f"{name} must not preload MCP dependencies",
                errors,
            )


def _validate_shared_rules(errors: list[str]) -> None:
    _require(
        _section(ROOT / "AGENTS.md", "## Documentation")
        == _section(ROOT / "CLAUDE.md", "## Documentation"),
        "AGENTS.md and CLAUDE.md documentation rules differ",
        errors,
    )
    for path in (
        ROOT / ".codex" / "agents" / "docs-maintainer.toml",
        ROOT / ".claude" / "agents" / "docs-maintainer.md",
    ):
        _require(
            not path.exists(), f"obsolete documentation agent remains: {path}", errors
        )

    forbidden = (
        "docsys",
        "flowform-doc-context",
        "flowform-doc-verification",
        "docs-maintainer",
    )
    for directory in (ROOT / ".claude" / "commands", ROOT / ".claude" / "rules"):
        for path in directory.rglob("*.md"):
            lowered = path.read_text(errors="replace").casefold()
            for token in forbidden:
                _require(
                    token not in lowered,
                    f"documentation workflow leaked into platform file: {path.relative_to(ROOT)}",
                    errors,
                )


def _validate_research_mcp(errors: list[str]) -> None:
    try:
        codex = tomllib.loads((ROOT / ".codex" / "config.toml").read_text())
        claude = json.loads((ROOT / ".mcp.json").read_text())
        claude_settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"invalid agent configuration: {exc}")
        return

    expected = "flowform-doc-research"
    codex_servers = codex.get("mcp_servers", {})
    claude_servers = claude.get("mcpServers", {})
    _require(
        expected in codex_servers,
        "Codex research MCP registration is missing",
        errors,
    )
    _require(
        expected in claude_servers,
        "Claude research MCP registration is missing",
        errors,
    )
    permissions = claude_settings.get("permissions", {}).get("allow", [])
    _require(
        "mcp__flowform-doc-research__research" in permissions,
        "Claude research MCP permission is missing",
        errors,
    )
    launcher = ROOT / "tools/bin/flowform-doc-research"
    _require(launcher.is_file(), "research MCP launcher is missing", errors)
    _require(
        (ROOT / "tools/bin/docsys-claude-sandbox").is_file(),
        "Claude SDK sandbox launcher is missing",
        errors,
    )
    removed = (
        "tools/bin/docsys_run.sh",
        "tools/bin/docsys_research_run.sh",
        "tools/bin/docsys_research_tools_run.sh",
        "tools/flowform_tools/docsys/mcp_server.py",
        "tools/flowform_tools/docsys/research_mcp_server.py",
        "tools/flowform_tools/docsys/research_tools_server.py",
    )
    for rel_path in removed:
        _require(
            not (ROOT / rel_path).exists(),
            f"obsolete MCP file remains: {rel_path}",
            errors,
        )


def _validate_bare_docsys_imports(errors: list[str]) -> None:
    """Protect commands that CI and commit hooks run without an environment."""
    for relative in BARE_DOCSYS_MODULES:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing bare-Python Docsys module: {relative}")
            continue
        try:
            tree = ast.parse(path.read_text(), filename=relative)
        except (OSError, SyntaxError) as exc:
            errors.append(f"cannot inspect bare-Python Docsys module {relative}: {exc}")
            continue
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.partition(".")[0])
        third_party = sorted(
            name
            for name in imported
            if name != "flowform_tools" and name not in sys.stdlib_module_names
        )
        if third_party:
            errors.append(
                f"bare-Python Docsys module imports third-party package(s): "
                f"{relative}: {', '.join(third_party)}"
            )


def _validate_commands(errors: list[str]) -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        capabilities = importlib.import_module(
            "flowform_tools.docsys.commands.capabilities"
        )
        catalog = importlib.import_module("flowform_tools.docsys.command_catalog")
        models = importlib.import_module("flowform_tools.docsys.research.models")
        prompt_module = importlib.import_module("flowform_tools.docsys.research.prompt")
        codex_provider = importlib.import_module("flowform_tools.docsys.research.codex")
        sessions = importlib.import_module(
            "flowform_tools.docsys.research.session_pool"
        )
    except Exception as exc:  # noqa: BLE001 - report any invalid command import
        errors.append(f"cannot load Docsys commands: {exc}")
        return

    expected_tools = (
        "tools/bin/docsys",
        "rg",
        "fd",
        "ast-grep",
        "jq",
        "yq",
        "sed",
        "nl",
    )
    actual_tools = tuple(tool["executable"] for tool in catalog.RESEARCH_CLI_TOOLS)
    _require(actual_tools == expected_tools, "research CLI inventory differs", errors)

    request = models.ResearchRequest(question="validation")
    prompt = prompt_module.build_prompt(request)
    for executable in expected_tools:
        _require(
            f"`{executable}`" in prompt,
            f"research prompt is missing {executable}",
            errors,
        )
    for excluded in ("git grep", "git log", "gh search", "fzf", "plocate", "recoll"):
        _require(excluded not in prompt, f"research prompt contains {excluded}", errors)
    _require("MCP" not in prompt, "research prompt must not depend on MCP", errors)

    payload = capabilities.inventory()
    _require(
        all(tool["available"] for tool in payload["research_session"]["commands"]),
        "one or more research CLI tools are unavailable",
        errors,
    )
    _require(
        all(tool["available"] for tool in payload["research_session"]["requirements"]),
        "one or more research MCP runtime requirements are unavailable",
        errors,
    )

    isolated_workspace = Path("/tmp/flowform-research-validation")
    command = codex_provider.codex_command(
        request,
        workspace=isolated_workspace,
        schema_path=Path("/tmp/flowform-research-schema.json"),
        output_path=Path("/tmp/flowform-research-output.json"),
    )
    command_text = " ".join(command)
    _require(
        command[command.index("--cd") + 1] == str(isolated_workspace),
        "research command must start outside the repository",
        errors,
    )
    for required in (
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox read-only",
        "project_doc_max_bytes=0",
        "memories.use_memories=false",
        'shell_environment_policy.inherit="all"',
    ):
        _require(
            required in command_text, f"research command is missing {required}", errors
        )
    for forbidden in ("mcp_servers.", "docsys_research_tools"):
        _require(
            forbidden not in command_text,
            f"research command contains {forbidden}",
            errors,
        )

    options = sessions._options(request, workspace=isolated_workspace)
    _require(
        Path(options.cli_path).name == "docsys-claude-sandbox",
        "Claude SDK must run through the read-only sandbox launcher",
        errors,
    )
    _require(
        options.setting_sources == [], "Claude SDK settings must be disabled", errors
    )
    _require(
        options.strict_mcp_config and options.mcp_servers == {},
        "Claude SDK session must not inherit MCP servers",
        errors,
    )
    _require(
        options.extra_args.get("no-session-persistence") is None
        and "no-session-persistence" in options.extra_args,
        "Claude SDK session persistence must be disabled",
        errors,
    )


def _validate_hooks(errors: list[str]) -> None:
    try:
        codex = json.loads((ROOT / ".codex" / "hooks.json").read_text()).get(
            "hooks", {}
        )
        claude = json.loads((ROOT / ".claude" / "settings.json").read_text()).get(
            "hooks", {}
        )
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid hook configuration: {exc}")
        return
    _require(codex == claude, "Codex and Claude hook configurations differ", errors)
    for command in _hook_commands(codex):
        _require(
            "docsys" not in command.casefold()
            and "tools/docs" not in command.casefold(),
            f"documentation lifecycle hook remains: {command}",
            errors,
        )
    shared_hook = ROOT / "tools/bin/agent-hook-python-quality"
    _require(shared_hook.is_file(), "shared Python quality hook is missing", errors)


def validate() -> list[str]:
    errors: list[str] = []
    _validate_skills(errors)
    _validate_shared_rules(errors)
    _validate_research_mcp(errors)
    _validate_bare_docsys_imports(errors)
    _validate_commands(errors)
    _validate_hooks(errors)
    _require(
        (ROOT / "tools/bin/docsys").is_file(), "Docsys launcher is missing", errors
    )
    _require(
        (
            ROOT / "tools/flowform_tools/docsys/maintenance/sync_agent_doc_config.py"
        ).is_file(),
        "documentation workflow sync command is missing",
        errors,
    )
    return errors


def main(argv: list[str] | None = None) -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "agent documentation workflow valid: shared skills, commands, and one-tool research MCP"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
