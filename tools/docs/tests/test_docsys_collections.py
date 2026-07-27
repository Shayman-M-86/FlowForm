from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tomllib
from docsys import mcp_server
from docsys.context import assess_reliability, build_context
from docsys.evidence import (
    EvidenceEntry,
    EvidenceSource,
    check_staged,
)
from docsys.impact import detect_impact
from docsys.freshness import CURRENT, Freshness
from docsys.debt import analyse, build_report, measure
from docsys.model import ROOT, DocSet, resolve_docs_root
from docsys.validate import all_findings


def _document(title: str, authority: str = "canonical", body: str = "") -> str:
    return f"""---
title: {title}
aliases: ["{title}"]
document_type: overview
status: scaffold
authority: {authority}
verified_evidence_digest: null
last_edited: 2026-07-27
tags: []
related_code: []
related_docs: []
---

# {title}

{body}
"""


class CollectionModelTests(unittest.TestCase):
    def test_impact_confidence_distinguishes_exact_and_broad_matches(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            code_dir = area / "implementation"
            code_dir.mkdir()
            exact_path = code_dir / "exact.py"
            broad_path = code_dir / "broad.py"

            (project / "exact.md").write_text(
                _document("Exact")
                .replace("status: scaffold", "status: draft")
                .replace(
                    "related_code: []",
                    'related_code: ["../../implementation/exact.py"]',
                )
            )
            (project / "broad.md").write_text(
                _document("Broad")
                .replace("status: scaffold", "status: draft")
                .replace(
                    "related_code: []",
                    'related_code: ["../../implementation/"]',
                )
            )
            docset = DocSet.load(docs_root)

            impacts = {
                item.doc.title: item.confidence
                for item in detect_impact(
                    [
                        exact_path.relative_to(ROOT).as_posix(),
                        broad_path.relative_to(ROOT).as_posix(),
                    ],
                    docset,
                )
            }

            self.assertEqual(impacts["Exact"], "high")
            self.assertEqual(impacts["Broad"], "medium")

    def test_staged_evidence_auto_refreshes_broad_impact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            code_path = area / "implementation" / "changed.py"
            code_path.parent.mkdir()
            doc_path = project / "broad.md"
            doc_path.write_text(
                _document("Broad")
                .replace("status: scaffold", "status: verified")
                .replace(
                    "verified_evidence_digest: null",
                    f"verified_evidence_digest: sha256:{'a' * 64}",
                )
                .replace(
                    "related_code: []",
                    'related_code: ["../../implementation/"]',
                )
            )
            code_rel = code_path.relative_to(ROOT).as_posix()
            source = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "b" * 40),
                },
                "staged index",
            )

            with patch(
                "docsys.evidence.EvidenceSource.from_index",
                return_value=source,
            ), patch(
                "docsys.evidence.DocSet.load",
                return_value=DocSet.load(docs_root),
            ), patch(
                "docsys.evidence._git_text",
                return_value=f"{code_rel}\n",
            ), patch(
                "docsys.evidence._has_unstaged",
                return_value=False,
            ), patch("docsys.evidence.subprocess.run"):
                result = check_staged(sync_invalidations=True)

            refreshed = DocSet.load(docs_root).docs[0]
            self.assertEqual(result, 0)
            self.assertEqual(refreshed.status, "verified")
            self.assertNotEqual(
                refreshed.verified_evidence_digest,
                f"sha256:{'a' * 64}",
            )

    def test_staged_evidence_invalidates_exact_impact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            code_path = area / "implementation.py"
            doc_path = project / "exact.md"
            doc_path.write_text(
                _document("Exact")
                .replace("status: scaffold", "status: verified")
                .replace(
                    "verified_evidence_digest: null",
                    f"verified_evidence_digest: sha256:{'a' * 64}",
                )
                .replace(
                    "related_code: []",
                    'related_code: ["../../implementation.py"]',
                )
            )
            code_rel = code_path.relative_to(ROOT).as_posix()
            source = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "b" * 40),
                },
                "staged index",
            )

            with patch(
                "docsys.evidence.EvidenceSource.from_index",
                return_value=source,
            ), patch(
                "docsys.evidence.DocSet.load",
                return_value=DocSet.load(docs_root),
            ), patch(
                "docsys.evidence._git_text",
                return_value=f"{code_rel}\n",
            ), patch(
                "docsys.evidence._has_unstaged",
                return_value=False,
            ), patch("docsys.evidence.subprocess.run"):
                result = check_staged(sync_invalidations=True)

            invalidated = DocSet.load(docs_root).docs[0]
            self.assertEqual(result, 1)
            self.assertEqual(invalidated.status, "draft")
            self.assertIsNone(invalidated.verified_evidence_digest)

    def test_evidence_digest_changes_only_for_matching_blobs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            docs_root.mkdir()
            doc_path = docs_root / "evidence.md"
            code_path = area / "implementation.py"
            doc_path.write_text(
                _document("Evidence", body="Checked implementation.").replace(
                    "related_code: []",
                    'related_code: ["../implementation.py"]',
                )
            )
            doc = DocSet.load(docs_root).docs[0]
            code_rel = code_path.relative_to(ROOT).as_posix()
            unrelated_rel = (area / "unrelated.py").relative_to(ROOT).as_posix()

            first = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "a" * 40),
                    unrelated_rel: EvidenceEntry(
                        unrelated_rel, "100644", "b" * 40
                    ),
                },
                "first",
            ).snapshot(doc)
            unrelated_changed = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "a" * 40),
                    unrelated_rel: EvidenceEntry(
                        unrelated_rel, "100644", "c" * 40
                    ),
                },
                "unrelated changed",
            ).snapshot(doc)
            evidence_changed = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "d" * 40),
                    unrelated_rel: EvidenceEntry(
                        unrelated_rel, "100644", "b" * 40
                    ),
                },
                "evidence changed",
            ).snapshot(doc)

            self.assertEqual(first.digest, unrelated_changed.digest)
            self.assertNotEqual(first.digest, evidence_changed.digest)
            self.assertEqual(first.files, (code_rel,))

    def test_active_docs_root_is_canonical_tree(self) -> None:
        self.assertEqual(resolve_docs_root(), (ROOT / "docs").resolve())
        with patch.dict("os.environ", {"FLOWFORM_DOCS_ROOT": "docs"}):
            self.assertEqual(resolve_docs_root(), (ROOT / "docs").resolve())

    def test_codex_and_claude_share_documentation_workflow(self) -> None:
        codex_skill = (
            ROOT / ".agents/skills/flowform-doc-context/SKILL.md"
        ).read_text()
        claude_skill = (
            ROOT / ".claude/skills/flowform-doc-context/SKILL.md"
        ).read_text()
        codex_verification_skill = (
            ROOT / ".agents/skills/flowform-doc-verification/SKILL.md"
        ).read_text()
        claude_verification_skill = (
            ROOT / ".claude/skills/flowform-doc-verification/SKILL.md"
        ).read_text()
        codex_agent = tomllib.loads(
            (ROOT / ".codex/agents/docs-maintainer.toml").read_text()
        )
        claude_agent = (
            ROOT / ".claude/agents/docs-maintainer.md"
        ).read_text()

        self.assertEqual(codex_skill, claude_skill)
        self.assertEqual(codex_verification_skill, claude_verification_skill)
        self.assertEqual(codex_agent["name"], "docs-maintainer")
        self.assertEqual(codex_agent["model"], "gpt-5.6-terra")
        self.assertIn("name: docs-maintainer", claude_agent)
        self.assertIn("model: sonnet", claude_agent)
        self.assertIn("- flowform-doc-context", claude_agent)

    def test_every_mcp_document_tool_accepts_docs_root(self) -> None:
        expected = {
            "search_docs",
            "get_document",
            "get_related",
            "get_task_context",
            "get_impacted_docs",
            "check_freshness",
            "documentation_debt",
            "doc_health",
        }
        schemas = {
            tool["name"]: tool["inputSchema"]["properties"]
            for tool in mcp_server.TOOLS
        }

        self.assertEqual(set(schemas), expected)
        for name in expected:
            self.assertIn("docs_root", schemas[name])

    def test_mcp_retrieval_and_reports_use_requested_docs_root(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "isolated-docs"
            docs_root.mkdir()
            (docs_root / "isolated-root.md").write_text(
                _document(
                    "Isolated root",
                    body="Unique documentation context. [[isolated-child|Isolated child]]",
                )
            )
            (docs_root / "isolated-child.md").write_text(
                _document("Isolated child", body="Child context.")
            )
            root_arg = docs_root.relative_to(ROOT).as_posix()

            document = mcp_server._tool_get_document(
                {"identifier": "Isolated root", "docs_root": root_arg}
            )
            related = mcp_server._tool_get_related(
                {"identifier": "Isolated root", "docs_root": root_arg}
            )
            context = mcp_server._tool_task_context(
                {"task": "unique documentation context", "docs_root": root_arg}
            )
            freshness = mcp_server._tool_freshness({"docs_root": root_arg})
            health = mcp_server._tool_health({"docs_root": root_arg})

            self.assertEqual(document["title"], "Isolated root")
            self.assertEqual(
                [item["title"] for item in related["related_documents"]],
                ["Isolated child"],
            )
            self.assertEqual(
                context["primary_documents"][0]["title"], "Isolated root"
            )
            self.assertEqual(freshness["counts"]["unknown"], 2)
            self.assertEqual(health["document_count"], 2)
            self.assertEqual(health["docs_root"], root_arg)

            with patch.object(
                mcp_server, "impact_report", return_value={"ok": True}
            ) as impact:
                self.assertEqual(
                    mcp_server._tool_impacted({"docs_root": root_arg}),
                    {"ok": True},
                )
            passed_docset = impact.call_args.kwargs["docset"]
            self.assertEqual(passed_docset.docs_dir, docs_root.resolve())

    def test_task_context_excludes_history_without_historical_intent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            docs_root.mkdir()
            (docs_root / "current.md").write_text(
                _document("Current encryption", body="response locator encryption")
            )
            historical = _document(
                "Historical encryption",
                authority="historical",
                body="response locator encryption security review",
            )
            (docs_root / "historical.md").write_text(historical)
            docset = DocSet.load(docs_root)

            current = build_context(
                task="response locator encryption",
                docset=docset,
            )
            history = build_context(
                task="historical response locator encryption",
                docset=docset,
            )

            self.assertNotIn(
                "Historical encryption",
                [doc.title for doc in current.primary],
            )
            self.assertIn(
                "Historical encryption",
                [doc.title for doc in history.primary],
            )

    def test_task_context_discloses_unreliable_working_tree_document(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            docs_root.mkdir()
            path = docs_root / "current.md"
            path.write_text(_document("Current access", body="survey access"))
            doc = DocSet.load(docs_root).docs[0]

            with patch(
                "docsys.context.gitutil.changed_files",
                return_value=type(
                    "Changed", (), {"files": [doc.rel_path]}
                )(),
            ), patch(
                "docsys.context.classify_document",
                return_value=Freshness(doc, CURRENT),
            ):
                reliability = assess_reliability([doc])

            self.assertEqual(reliability["assessment"], "unreliable")
            self.assertTrue(reliability["requires_disclosure"])
            self.assertEqual(
                reliability["message"],
                "I think the documentation is unreliable for this question.",
            )

    def test_task_context_marks_clean_draft_as_provisional(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            docs_root.mkdir()
            path = docs_root / "current.md"
            path.write_text(
                _document("Current access", body="survey access").replace(
                    "status: scaffold", "status: draft"
                )
            )
            doc = DocSet.load(docs_root).docs[0]

            with patch(
                "docsys.context.gitutil.changed_files",
                return_value=type("Changed", (), {"files": []})(),
            ), patch(
                "docsys.context.classify_document",
                return_value=Freshness(doc, CURRENT),
            ):
                reliability = assess_reliability([doc])

            self.assertEqual(reliability["assessment"], "provisional")
            self.assertTrue(reliability["requires_disclosure"])

    def test_parent_collection_and_profile_validation(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            child_dir = docs_root / "project-knowledge" / "backend"
            child_dir.mkdir(parents=True)
            (docs_root / "docs-index.md").write_text(_document("Root"))
            (docs_root / "project-knowledge" / "project-knowledge-index.md").write_text(
                _document("Project Knowledge")
            )
            (child_dir / "backend-index.md").write_text(_document("Backend"))

            docset = DocSet.load(docs_root)
            backend = docset.by_title("Backend")
            self.assertIsNotNone(backend)
            assert backend is not None
            self.assertEqual(backend.collection, "project-knowledge")
            self.assertEqual(
                docset.inferred_parent(backend).title,  # type: ignore[union-attr]
                "Project Knowledge",
            )
            self.assertEqual(all_findings(docset, "ci"), [])

    def test_split_candidate_is_advisory_and_explainable(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            topic_dir = docs_root / "project-knowledge"
            topic_dir.mkdir(parents=True)
            sections = "\n\n".join(
                f"## Topic {number}\n\n" + "focused evidence " * 120
                for number in range(1, 16)
            )
            (docs_root / "docs-index.md").write_text(_document("Root"))
            (topic_dir / "project-knowledge-index.md").write_text(
                _document("Project Knowledge")
            )
            (topic_dir / "large-overview.md").write_text(
                _document("Large overview", body=sections)
            )
            docset = DocSet.load(docs_root)
            doc = docset.by_title("Large overview")
            assert doc is not None
            findings = analyse(doc, measure(doc), suggest_splits=True)

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].code, "split_candidate")
            self.assertIn(findings[0].severity, {"warning", "strong_recommendation"})
            self.assertGreaterEqual(len(findings[0].evidence), 5)
            self.assertEqual(len(findings[0].suggested_children), 16)
            self.assertTrue(
                findings[0].suggested_children[0].endswith(
                    "large-overview/large-overview-index.md"
                )
            )

    def test_workspace_optional_metadata_stays_advisory_in_ci(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            workspace = docs_root / "development-workspace"
            workspace.mkdir(parents=True)
            (docs_root / "docs-index.md").write_text(_document("Root"))
            incomplete = _document(
                "Workspace", authority="working"
            )
            for optional_line in (
                'aliases: ["Workspace"]\n',
                "authority: working\n",
                "verified_evidence_digest: null\n",
                "related_code: []\n",
                "related_docs: []\n",
            ):
                incomplete = incomplete.replace(optional_line, "")
            (workspace / "development-workspace-index.md").write_text(incomplete)
            findings = all_findings(DocSet.load(docs_root), "ci")

            self.assertEqual(
                {item.code for item in findings},
                {
                    "missing_aliases",
                    "missing_authority",
                    "missing_related_code",
                    "missing_related_docs",
                    "missing_verified_evidence_digest",
                },
            )
            self.assertTrue(all(item.severity == "warning" for item in findings))

    def test_workspace_verification_is_advisory_not_a_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            workspace = docs_root / "development-workspace"
            workspace.mkdir(parents=True)
            (docs_root / "docs-index.md").write_text(_document("Root"))
            document = _document("Workspace", authority="working").replace(
                "status: scaffold", "status: verified"
            ).replace(
                "verified_evidence_digest: null",
                f"verified_evidence_digest: sha256:{'a' * 64}",
            )
            (workspace / "development-workspace-index.md").write_text(document)

            findings = all_findings(DocSet.load(docs_root), "commit")
            verification = [
                item
                for item in findings
                if item.code == "workspace_verification_metadata"
            ]

            self.assertEqual(len(verification), 1)
            self.assertEqual(verification[0].severity, "warning")
            self.assertFalse(
                any(item.severity == "error" for item in findings),
                findings,
            )

    def test_empty_debt_path_filter_selects_no_documents(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            docs_root.mkdir()
            (docs_root / "docs-index.md").write_text(_document("Root"))

            report = build_report(DocSet.load(docs_root), paths=set())

            self.assertEqual(report["document_count"], 0)
            self.assertEqual(report["documents"], [])


if __name__ == "__main__":
    unittest.main()
