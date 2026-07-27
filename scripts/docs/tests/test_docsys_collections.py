from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docsys.debt import analyse, build_report, measure
from docsys.model import ROOT, DocSet
from docsys.validate import all_findings


def _document(title: str, authority: str = "canonical", body: str = "") -> str:
    return f"""---
title: {title}
aliases: ["{title}"]
document_type: overview
status: scaffold
authority: {authority}
verified_against_commit: null
tags: []
related_code: []
related_docs: []
---

# {title}

{body}
"""


class CollectionModelTests(unittest.TestCase):
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
                "verified_against_commit: null\n",
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
                    "missing_verified_against_commit",
                },
            )
            self.assertTrue(all(item.severity == "warning" for item in findings))

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
