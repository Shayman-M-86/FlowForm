#!/usr/bin/env python3
"""Collection-aware structural validation for FlowForm documentation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from .model import (
    ALLOWED_CONFIDENCE,
    ALLOWED_STATUS,
    REQUIRED_KEYS,
    ROOT,
    TAG_VOCABULARY,
    DocSet,
    folder_head_path,
    strip_code,
    resolve_docs_root,
)
from .model import _MD_LINK_RE, _WIKI_LINK_RE

PROFILES = ("editing", "project-knowledge", "workspace", "commit", "ci")


@dataclass
class Finding:
    path: str
    kind: str
    message: str
    code: str = "unspecified"
    collection: str = "legacy"
    severity: str = "error"


def _severity(code: str, collection: str, profile: str) -> str:
    """Map a shared rule to profile/collection severity."""
    workspace_advisory = {
        "missing_aliases",
        "missing_authority",
        "missing_related_code",
        "missing_related_docs",
        "missing_verified_against_commit",
    }
    if profile == "editing":
        return "warning"
    if profile == "project-knowledge":
        return "error" if collection in {"project-knowledge", "root"} else "warning"
    if profile == "workspace":
        if collection == "development-workspace" and code in workspace_advisory:
            return "warning"
        return "error" if collection in {"development-workspace", "root"} else "warning"
    if collection == "development-workspace" and code in workspace_advisory:
        return "warning"
    # Commit and CI treat objective structural defects as gates in both
    # collections. Maintainability debt is intentionally handled elsewhere.
    return "error"


def _finding(doc, kind: str, code: str, message: str, profile: str) -> Finding:
    return Finding(
        doc.rel_path,
        kind,
        message,
        code,
        doc.collection,
        _severity(code, doc.collection, profile),
    )


def metadata_findings(
    docset: DocSet, profile: str = "editing"
) -> list[Finding]:
    findings: list[Finding] = []
    titles: dict[str, str] = {}

    for path in docset.unparsed_paths:
        rel = path.relative_to(ROOT).as_posix()
        collection = (
            path.relative_to(docset.docs_dir).parts[0]
            if path.parent != docset.docs_dir
            else "root"
        )
        findings.append(
            Finding(
                rel,
                "metadata",
                "missing or unterminated front matter",
                "invalid_front_matter",
                collection,
                _severity("invalid_front_matter", collection, profile),
            )
        )

    for doc in docset.docs:
        for key in REQUIRED_KEYS:
            if key not in doc.front_matter:
                findings.append(
                    _finding(
                        doc,
                        "metadata",
                        f"missing_{key}",
                        f"missing key '{key}'",
                        profile,
                    )
                )
        if doc.status and doc.status not in ALLOWED_STATUS:
            findings.append(
                _finding(
                    doc,
                    "metadata",
                    "invalid_status",
                    f"invalid status '{doc.status}'",
                    profile,
                )
            )
        for tag in doc.tags:
            if tag not in TAG_VOCABULARY:
                findings.append(
                    _finding(
                        doc,
                        "metadata",
                        "invalid_tag",
                        f"tag '{tag}' not in vocabulary",
                        profile,
                    )
                )
        confidence = doc.front_matter.get("code_confidence")
        if confidence is not None and str(confidence).lower() not in ALLOWED_CONFIDENCE:
            findings.append(
                _finding(
                    doc,
                    "metadata",
                    "invalid_code_confidence",
                    f"code_confidence '{confidence}' not in {sorted(ALLOWED_CONFIDENCE)}",
                    profile,
                )
            )
        if not doc.title:
            findings.append(
                _finding(
                    doc, "metadata", "missing_title", "missing or empty title", profile
                )
            )
            continue
        if "aliases" in doc.front_matter:
            aliases = doc.front_matter["aliases"]
            if not isinstance(aliases, list):
                findings.append(
                    _finding(
                        doc,
                        "metadata",
                        "invalid_aliases",
                        "aliases must be a list",
                        profile,
                    )
                )
            elif doc.title.casefold() not in {
                str(alias).casefold() for alias in aliases
            }:
                findings.append(
                    _finding(
                        doc,
                        "metadata",
                        "missing_title_alias",
                        f"aliases must include the document title '{doc.title}'",
                        profile,
                    )
                )
        key = doc.title.casefold()
        if key in titles:
            findings.append(
                _finding(
                    doc,
                    "metadata",
                    "duplicate_title",
                    f"duplicate title '{doc.title}' (also {titles[key]})",
                    profile,
                )
            )
        else:
            titles[key] = doc.rel_path

        if (
            docset.uses_collection_model
            and doc.collection == "legacy"
        ):
            findings.append(
                _finding(
                    doc,
                    "metadata",
                    "invalid_collection",
                    "document is outside the two documentation collections",
                    profile,
                )
            )
        if (
            doc.collection == "development-workspace"
            and doc.authority.casefold() == "canonical"
        ):
            findings.append(
                _finding(
                    doc,
                    "metadata",
                    "workspace_canonical_authority",
                    "workspace documents must not claim canonical authority",
                    profile,
                )
            )

    for doc in docset.docs:
        for entry in doc.related_docs:
            if str(entry).casefold() == doc.title.casefold():
                findings.append(
                    _finding(
                        doc,
                        "metadata",
                        "self_related_doc",
                        "related_docs must not reference the document itself",
                        profile,
                    )
                )
            elif str(entry).casefold() not in titles:
                findings.append(
                    _finding(
                        doc,
                        "metadata",
                        "unresolved_related_doc",
                        f"related_docs '{entry}' matches no title",
                        profile,
                    )
                )
    return findings


def structural_findings(
    docset: DocSet, profile: str = "editing"
) -> list[Finding]:
    if not docset.uses_collection_model:
        return []
    findings: list[Finding] = []
    markdown_dirs = {path.parent for path in docset.docs_dir.rglob("*.md")}
    for directory in sorted(markdown_dirs):
        expected_head = folder_head_path(directory)
        if not expected_head.exists():
            relative = directory.relative_to(ROOT).as_posix()
            collection = (
                directory.relative_to(docset.docs_dir).parts[0]
                if directory != docset.docs_dir
                else "root"
            )
            findings.append(
                Finding(
                    relative,
                    "structure",
                    "documentation directory has no "
                    f"{expected_head.name} folder head",
                    "missing_folder_head",
                    collection,
                    _severity("missing_folder_head", collection, profile),
                )
            )
    for doc in docset.docs:
        declared = doc.front_matter.get("parent")
        inferred = docset.inferred_parent(doc)
        if declared is not None and str(declared).casefold() != (
            inferred.title.casefold() if inferred else ""
        ):
            findings.append(
                _finding(
                    doc,
                    "structure",
                    "parent_mismatch",
                    f"declared parent '{declared}' does not match "
                    f"'{inferred.title if inferred else None}'",
                    profile,
                )
            )
        if doc.collection != "root" and inferred is None:
            findings.append(
                _finding(
                    doc,
                    "structure",
                    "missing_parent",
                    "no structural parent can be inferred",
                    profile,
                )
            )
    return findings


def link_findings(docset: DocSet, profile: str = "editing") -> list[Finding]:
    findings: list[Finding] = []
    for doc in docset.docs:
        body = strip_code(doc.body)
        for target in _WIKI_LINK_RE.findall(body):
            if docset.resolve_wiki(target.strip()) is None:
                findings.append(
                    _finding(
                        doc,
                        "link",
                        "unresolved_wiki_link",
                        f"unresolved wiki link [[{target}]]",
                        profile,
                    )
                )
        for link in _MD_LINK_RE.findall(body):
            if "://" in link or link.startswith(("#", "mailto:")):
                continue
            target = link.split("#")[0]
            if target and not (doc.path.parent / target).resolve().exists():
                findings.append(
                    _finding(
                        doc,
                        "link",
                        "broken_markdown_link",
                        f"broken link {link}",
                        profile,
                    )
                )
    return findings


def all_findings(
    docset: DocSet | None = None, profile: str = "editing"
) -> list[Finding]:
    docset = docset or DocSet.load()
    return (
        metadata_findings(docset, profile)
        + structural_findings(docset, profile)
        + link_findings(docset, profile)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docsys validate")
    parser.add_argument("--docs-root", default="docs")
    parser.add_argument("--profile", choices=PROFILES, default="editing")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    docs_dir = resolve_docs_root(args.docs_root)
    docset = DocSet.load(docs_dir)
    findings = all_findings(docset, args.profile)
    if args.format == "json":
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        for item in findings:
            print(
                f"{item.severity.upper():7} {item.path}: "
                f"{item.code}: {item.message}"
            )
        errors = sum(item.severity == "error" for item in findings)
        warnings = sum(item.severity == "warning" for item in findings)
        print(
            f"checked {len(docset.docs)} documents with profile "
            f"{args.profile}: {errors} error(s), {warnings} warning(s)"
        )
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
