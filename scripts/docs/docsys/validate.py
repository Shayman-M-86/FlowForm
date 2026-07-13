#!/usr/bin/env python3
"""Structural validation reused by the dashboard and (optionally) CI.

This mirrors the checks in the existing dependency-free validators
(``validate-doc-metadata.py`` / ``validate-doc-links.py``) but returns
structured findings instead of printing, so the health dashboard can render
them. The standalone validators remain the canonical CI gate; this module is
the programmatic view of the same rules, plus the extended tooling fields
(``change_triggers``, ``exclusions``, ``code_confidence``).
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import (
    ALLOWED_CONFIDENCE,
    ALLOWED_STATUS,
    REQUIRED_KEYS,
    TAG_VOCABULARY,
    DocSet,
    strip_code,
)
from .model import _MD_LINK_RE, _WIKI_LINK_RE


@dataclass
class Finding:
    path: str
    kind: str  # "metadata" | "link"
    message: str


def metadata_findings(docset: DocSet) -> list[Finding]:
    findings: list[Finding] = []
    titles = {}
    for d in docset.docs:
        for key in REQUIRED_KEYS:
            if key not in d.front_matter:
                findings.append(Finding(d.rel_path, "metadata", f"missing key '{key}'"))
        if d.status and d.status not in ALLOWED_STATUS:
            findings.append(
                Finding(d.rel_path, "metadata", f"invalid status '{d.status}'")
            )
        for tag in d.tags:
            if tag not in TAG_VOCABULARY:
                findings.append(
                    Finding(d.rel_path, "metadata", f"tag '{tag}' not in vocabulary")
                )
        conf = d.front_matter.get("code_confidence")
        if conf is not None and str(conf).lower() not in ALLOWED_CONFIDENCE:
            findings.append(
                Finding(
                    d.rel_path,
                    "metadata",
                    f"code_confidence '{conf}' not in {sorted(ALLOWED_CONFIDENCE)}",
                )
            )
        if not d.title:
            findings.append(Finding(d.rel_path, "metadata", "missing or empty title"))
            continue
        key = d.title.casefold()
        if key in titles:
            findings.append(
                Finding(
                    d.rel_path,
                    "metadata",
                    f"duplicate title '{d.title}' (also {titles[key]})",
                )
            )
        else:
            titles[key] = d.rel_path

    for d in docset.docs:
        for entry in d.related_docs:
            if entry.casefold() not in titles:
                findings.append(
                    Finding(
                        d.rel_path,
                        "metadata",
                        f"related_docs '{entry}' matches no title",
                    )
                )
    return findings


def link_findings(docset: DocSet) -> list[Finding]:
    findings: list[Finding] = []
    titles = {d.title.casefold() for d in docset.docs if d.title}
    for d in docset.docs:
        body = strip_code(d.body)
        for target in _WIKI_LINK_RE.findall(body):
            if target.strip().casefold() not in titles:
                findings.append(
                    Finding(d.rel_path, "link", f"unresolved wiki link [[{target}]]")
                )
        for link in _MD_LINK_RE.findall(body):
            if "://" in link or link.startswith(("#", "mailto:")):
                continue
            target = link.split("#")[0]
            if target and not (d.path.parent / target).resolve().exists():
                findings.append(Finding(d.rel_path, "link", f"broken link {link}"))
    return findings


def all_findings(docset: DocSet | None = None) -> list[Finding]:
    docset = docset or DocSet.load()
    return metadata_findings(docset) + link_findings(docset)
