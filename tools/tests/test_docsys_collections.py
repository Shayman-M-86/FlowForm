from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flowform_tools.docsys.commands.debt import (
    _DEFAULT_POLICY,
    analyse,
    build_report,
    measure,
)
from flowform_tools.docsys.commands.evidence import (
    EvidenceEntry,
    EvidenceSource,
    check_last_edited_staged,
    check_staged,
    promote_staged,
)
from flowform_tools.docsys.commands.impact import detect_impact
from flowform_tools.docsys.commands.review import build_staged_review
from flowform_tools.docsys.commands.validate import all_findings, metadata_findings
from flowform_tools.docsys.core.model import (
    ROOT,
    DocSet,
    is_inert_archive_repo_path,
    parse_front_matter,
    resolve_docs_root,
)


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
    def test_front_matter_normalises_null_and_rejects_nested_mappings(self) -> None:
        metadata = parse_front_matter(
            "---\ntitle: Example\nverified_evidence_digest: null\n---\n"
        )

        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertIsNone(metadata["verified_evidence_digest"])
        with self.assertRaisesRegex(ValueError, "nested mappings"):
            parse_front_matter("---\ntitle: Example\nmeta:\n  sub: value\n---\n")

    def test_related_code_accepts_only_exact_existing_repository_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            implementation = area / "implementation"
            implementation.mkdir()
            (implementation / "exact.py").write_text("checked = True\n")

            entries = {
                "Exact": "../../implementation/exact.py",
                "Directory": "../../implementation",
                "Trailing directory": "../../implementation/",
                "Glob": "../../implementation/*.py",
                "Missing": "../../implementation/missing.py",
            }
            for title, entry in entries.items():
                (project / f"{title.casefold().replace(' ', '-')}.md").write_text(
                    _document(title).replace(
                        "related_code: []",
                        f'related_code: ["{entry}"]',
                    )
                )

            findings = [
                item
                for item in metadata_findings(DocSet.load(docs_root), "ci")
                if item.code == "related_code_not_file"
            ]

            self.assertEqual(
                {item.path.rsplit("/", 1)[-1] for item in findings},
                {
                    "directory.md",
                    "trailing-directory.md",
                    "glob.md",
                    "missing.md",
                },
            )
            self.assertTrue(all(item.severity == "error" for item in findings))

    def test_impact_confidence_distinguishes_exact_code_and_broad_trigger(
        self,
    ) -> None:
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
                    'related_code: []\nchange_triggers: ["../../implementation/"]',
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
            self.assertEqual(impacts["Broad"], "low")

    def test_staged_review_uses_correlated_signals_not_change_size(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            code_dir = area / "implementation"
            code_dir.mkdir()
            first_code = code_dir / "first.py"
            second_code = code_dir / "second.py"
            first_code.write_text("first = True\n")
            second_code.write_text("second = True\n")
            first_doc = project / "first.md"
            second_doc = project / "second.md"
            first_doc.write_text(
                _document("First")
                .replace("status: scaffold", "status: draft")
                .replace(
                    "related_code: []",
                    'related_code: ["../../implementation/first.py"]',
                )
            )
            second_doc.write_text(
                _document("Second")
                .replace("status: scaffold", "status: draft")
                .replace(
                    "related_code: []",
                    'related_code: ["../../implementation/second.py"]',
                )
            )
            docset = DocSet.load(docs_root)
            source = EvidenceSource({}, "test index")
            first_rel = first_code.relative_to(ROOT).as_posix()
            second_rel = second_code.relative_to(ROOT).as_posix()

            small = build_staged_review(
                staged_paths=[first_rel],
                docset=docset,
                source=source,
            )
            correlated = build_staged_review(
                staged_paths=[first_rel, second_rel],
                docset=docset,
                source=source,
            )

            self.assertFalse(small.recommended)
            self.assertEqual(len(small.candidates), 1)
            self.assertTrue(correlated.recommended)
            self.assertIn("direct-evidence", correlated.reasons[0])

    def test_staged_review_escalates_impacted_complex_document(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            code_path = area / "implementation.py"
            code_path.write_text("changed = True\n")
            sections = "\n\n".join(
                f"## Topic {number}\n\n" + "focused evidence " * 120
                for number in range(1, 16)
            )
            doc_path = project / "complex.md"
            doc_path.write_text(
                _document("Complex", body=sections)
                .replace("status: scaffold", "status: draft")
                .replace(
                    "related_code: []",
                    'related_code: ["../../implementation.py"]',
                )
            )
            code_rel = code_path.relative_to(ROOT).as_posix()

            review = build_staged_review(
                staged_paths=[code_rel],
                docset=DocSet.load(docs_root),
                source=EvidenceSource({}, "test index"),
            )

            self.assertTrue(review.recommended)
            self.assertIn("complexity debt", " ".join(review.reasons))
            self.assertTrue(review.candidates[0].debt_findings)

    def test_staged_review_escalates_broad_impact_with_stale_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            code_path = area / "implementation" / "changed.py"
            code_path.parent.mkdir()
            code_path.write_text("changed = True\n")
            doc_path = project / "verified.md"
            doc_path.write_text(
                _document("Verified")
                .replace("status: scaffold", "status: verified")
                .replace(
                    "verified_evidence_digest: null",
                    f"verified_evidence_digest: sha256:{'a' * 64}",
                )
                .replace(
                    "related_code: []",
                    'related_code: []\nchange_triggers: ["../../implementation/"]',
                )
            )
            code_rel = code_path.relative_to(ROOT).as_posix()
            source = EvidenceSource(
                {code_rel: EvidenceEntry(code_rel, "100644", "b" * 40)},
                "test index",
            )

            review = build_staged_review(
                staged_paths=[code_rel],
                docset=DocSet.load(docs_root),
                source=source,
            )

            self.assertTrue(review.recommended)
            self.assertEqual(review.candidates[0].confidence, "low")
            self.assertEqual(review.candidates[0].freshness, "likely stale")
            self.assertIn("staged evidence snapshot", " ".join(review.reasons))

    def test_staged_review_ignores_a_document_already_staged(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            area = Path(temporary)
            docs_root = area / "docs"
            project = docs_root / "project-knowledge"
            project.mkdir(parents=True)
            code_path = area / "implementation.py"
            code_path.write_text("changed = True\n")
            doc_path = project / "updated.md"
            doc_path.write_text(
                _document("Updated").replace(
                    "related_code: []",
                    'related_code: ["../../implementation.py"]',
                )
            )

            review = build_staged_review(
                staged_paths=[
                    code_path.relative_to(ROOT).as_posix(),
                    doc_path.relative_to(ROOT).as_posix(),
                ],
                docset=DocSet.load(docs_root),
                source=EvidenceSource({}, "test index"),
            )

            self.assertFalse(review.recommended)
            self.assertEqual(review.candidates, [])

    def test_staged_evidence_ignores_broad_trigger_without_writing(self) -> None:
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
                    'related_code: []\nchange_triggers: ["../../implementation/"]',
                )
            )
            code_rel = code_path.relative_to(ROOT).as_posix()
            source = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "b" * 40),
                },
                "staged index",
            )

            with (
                patch(
                    "flowform_tools.docsys.commands.evidence.EvidenceSource.from_index",
                    return_value=source,
                ),
                patch(
                    "flowform_tools.docsys.commands.evidence.DocSet.load",
                    return_value=DocSet.load(docs_root),
                ),
                patch(
                    "flowform_tools.docsys.commands.evidence._git_text",
                    return_value=f"{code_rel}\n",
                ),
                patch(
                    "flowform_tools.docsys.commands.evidence._set_metadata"
                ) as set_metadata,
            ):
                result = check_staged()

            unchanged = DocSet.load(docs_root).docs[0]
            self.assertEqual(result, 0)
            self.assertEqual(unchanged.status, "verified")
            self.assertEqual(
                unchanged.verified_evidence_digest,
                f"sha256:{'a' * 64}",
            )
            set_metadata.assert_not_called()

    def test_staged_evidence_reports_exact_impact_without_writing(self) -> None:
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

            with (
                patch(
                    "flowform_tools.docsys.commands.evidence.EvidenceSource.from_index",
                    return_value=source,
                ),
                patch(
                    "flowform_tools.docsys.commands.evidence.DocSet.load",
                    return_value=DocSet.load(docs_root),
                ),
                patch(
                    "flowform_tools.docsys.commands.evidence._git_text",
                    return_value=f"{code_rel}\n",
                ),
                patch(
                    "flowform_tools.docsys.commands.evidence._set_metadata"
                ) as set_metadata,
            ):
                result = check_staged()

            unchanged = DocSet.load(docs_root).docs[0]
            self.assertEqual(result, 1)
            self.assertEqual(unchanged.status, "verified")
            self.assertEqual(
                unchanged.verified_evidence_digest,
                f"sha256:{'a' * 64}",
            )
            set_metadata.assert_not_called()

    def test_last_edited_check_does_not_write_or_stage(self) -> None:
        staged = "docs/project-knowledge/example.md"
        old_document = _document("Example").replace(
            "last_edited: 2026-07-27",
            "last_edited: 2026-07-26",
        )

        with (
            patch(
                "flowform_tools.docsys.commands.evidence._git_text",
                side_effect=[f"{staged}\n", old_document],
            ),
            patch(
                "flowform_tools.docsys.commands.evidence._today",
                return_value="2026-07-27",
            ),
            patch(
                "flowform_tools.docsys.commands.evidence._set_last_edited"
            ) as set_last_edited,
            patch("flowform_tools.docsys.core.gitutil.subprocess.run") as run,
        ):
            result = check_last_edited_staged()

        self.assertEqual(result, 1)
        set_last_edited.assert_not_called()
        run.assert_not_called()

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
                    unrelated_rel: EvidenceEntry(unrelated_rel, "100644", "b" * 40),
                },
                "first",
            ).snapshot(doc)
            unrelated_changed = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "a" * 40),
                    unrelated_rel: EvidenceEntry(unrelated_rel, "100644", "c" * 40),
                },
                "unrelated changed",
            ).snapshot(doc)
            evidence_changed = EvidenceSource(
                {
                    code_rel: EvidenceEntry(code_rel, "100644", "d" * 40),
                    unrelated_rel: EvidenceEntry(unrelated_rel, "100644", "b" * 40),
                },
                "evidence changed",
            ).snapshot(doc)

            self.assertEqual(first.digest, unrelated_changed.digest)
            self.assertNotEqual(first.digest, evidence_changed.digest)
            self.assertEqual(first.files, (code_rel,))

    def test_promote_can_stage_only_the_selected_document(self) -> None:
        project_knowledge = ROOT / "docs" / "project-knowledge"
        with tempfile.TemporaryDirectory(dir=project_knowledge) as temporary:
            doc_path = Path(temporary) / "promote.md"
            doc_path.write_text(
                _document("Promote", body="Reviewed claim.").replace(
                    "related_code: []",
                    'related_code: ["../../../AGENTS.md"]',
                )
            )
            rel = doc_path.relative_to(ROOT).as_posix()
            source = EvidenceSource(
                {"AGENTS.md": EvidenceEntry("AGENTS.md", "100644", "a" * 40)},
                "staged",
            )

            with (
                patch(
                    "flowform_tools.docsys.commands.evidence.EvidenceSource.from_index",
                    return_value=source,
                ),
                patch(
                    "flowform_tools.docsys.core.gitutil.run_bytes",
                    return_value=b"",
                ) as git_bytes,
                patch(
                    "flowform_tools.docsys.commands.evidence._today",
                    return_value="2026-07-29",
                ),
            ):
                result = promote_staged([rel], stage=True)

            self.assertEqual(result, 0)
            git_bytes.assert_called_once_with(["add", "--", rel])
            promoted = doc_path.read_text()
            self.assertIn("status: verified", promoted)
            self.assertIn("last_edited: 2026-07-29", promoted)
            self.assertRegex(
                promoted,
                r"verified_evidence_digest: sha256:[0-9a-f]{64}",
            )

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
        codex_commit_skill = (ROOT / ".agents/skills/commit/SKILL.md").read_text()
        claude_commit_skill = (ROOT / ".claude/skills/commit/SKILL.md").read_text()
        claude_commit_command = (ROOT / ".claude/commands/commit.md").read_text()
        self.assertEqual(codex_skill, claude_skill)
        self.assertEqual(codex_verification_skill, claude_verification_skill)
        self.assertEqual(codex_commit_skill, claude_commit_skill)
        self.assertIn(
            ".claude/skills/commit/SKILL.md",
            claude_commit_command,
        )
        self.assertFalse((ROOT / ".codex/agents/docs-maintainer.toml").exists())
        self.assertFalse((ROOT / ".claude/agents/docs-maintainer.md").exists())
        self.assertIn("tools/bin/docsys research", codex_skill)

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
                findings[0]
                .suggested_children[0]
                .endswith("large-overview/large-overview-index.md")
            )

    def test_debt_defaults_to_project_knowledge(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            project = docs_root / "project-knowledge"
            workspace = docs_root / "development-workspace"
            project.mkdir(parents=True)
            workspace.mkdir()
            (docs_root / "docs-index.md").write_text(_document("Root"))
            (project / "project-knowledge-index.md").write_text(
                _document("Project Knowledge")
            )
            (workspace / "development-workspace-index.md").write_text(
                _document("Development workspace", authority="working")
            )
            docset = DocSet.load(docs_root)

            default_report = build_report(docset)
            self.assertEqual(default_report["document_count"], 1)
            self.assertEqual(
                default_report["documents"][0]["metrics"]["collection"],
                "project-knowledge",
            )

    def test_default_debt_policy_remains_moderately_strict(self) -> None:
        self.assertEqual(
            _DEFAULT_POLICY,
            {
                "max_words": 1600,
                "max_major_sections": 6,
                "large_section_words": 300,
                "large_section_count": 2,
                "max_code_ratio": 0.4,
                "max_code_roots": 4,
            },
        )

    def test_workspace_optional_metadata_stays_advisory_in_ci(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            workspace = docs_root / "development-workspace"
            workspace.mkdir(parents=True)
            (docs_root / "docs-index.md").write_text(_document("Root"))
            incomplete = _document("Workspace", authority="working")
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

    def test_verbatim_old_docs_archive_is_excluded_from_docsys(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            workspace = docs_root / "development-workspace"
            archive = workspace / "archive" / "old-docs" / "nested"
            archive.mkdir(parents=True)
            (docs_root / "docs-index.md").write_text(_document("Root"))
            (workspace / "development-workspace-index.md").write_text(
                _document("Development workspace", authority="working")
            )
            (archive / "legacy.md").write_text("# No front matter\n\n[broken](missing.md)\n")

            docset = DocSet.load(docs_root)

            self.assertEqual(len(docset.unparsed_paths), 0)
            self.assertFalse(any("old-docs" in doc.rel_path for doc in docset.docs))
            self.assertFalse(
                any(item.path.endswith("old-docs/nested") for item in all_findings(docset, "ci"))
            )
            self.assertTrue(
                is_inert_archive_repo_path(
                    "docs/development-workspace/archive/old-docs/nested/legacy.md"
                )
            )
            self.assertFalse(
                is_inert_archive_repo_path(
                    "docs/development-workspace/archive/security-review-1.md"
                )
            )

    def test_workspace_verification_is_advisory_not_a_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            workspace = docs_root / "development-workspace"
            workspace.mkdir(parents=True)
            (docs_root / "docs-index.md").write_text(_document("Root"))
            document = (
                _document("Workspace", authority="working")
                .replace("status: scaffold", "status: verified")
                .replace(
                    "verified_evidence_digest: null",
                    f"verified_evidence_digest: sha256:{'a' * 64}",
                )
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
