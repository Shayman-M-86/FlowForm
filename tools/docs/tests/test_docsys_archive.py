"""Imported legacy snapshots must not enter the managed documentation checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docsys.evidence import check_last_edited_staged, sync_last_edited_staged
from docsys.model import ROOT, DocSet, is_ignored_document
from docsys.validate import all_findings


class ArchiveImportTests(unittest.TestCase):
    def test_legacy_imports_do_not_affect_discovery_or_validation(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            docs_root = Path(temporary) / "docs"
            archive = docs_root / "development-workspace" / "archive"
            legacy = archive / "old-docs" / "nested"
            legacy.mkdir(parents=True)
            for directory in (docs_root, archive.parent, archive):
                title = directory.name
                (directory / f"{title}-index.md").write_text(
                    f'---\ntitle: {title}\naliases: ["{title}"]\n'
                    "document_type: overview\nstatus: draft\nauthority: working\n"
                    "verified_evidence_digest: null\nlast_edited: 2026-11-17\n"
                    "tags: []\nrelated_code: []\nrelated_docs: []\n---\n"
                    f"\n# {title}\n"
                )
            (legacy / "unparsed.md").write_text("Historical file without metadata.\n")
            (legacy / "duplicate.md").write_text(
                "---\ntitle: archive\nstatus: outdated\n---\n# archive\n"
            )

            docset = DocSet.load(docs_root)

            self.assertEqual(len(docset.docs), 3)
            self.assertEqual(docset.unparsed_paths, [])
            self.assertEqual(all_findings(docset, "commit"), [])
            self.assertEqual(
                docset.by_title("archive").path, archive / "archive-index.md"
            )

    def test_exclusion_is_limited_to_legacy_imports(self) -> None:
        for relative in (
            "development-workspace/archive/archive-index.md",
            "development-workspace/archive/completed/completed-index.md",
            "development-workspace/archive/old-docs-notes.md",
            "project-knowledge/old-docs/example.md",
        ):
            with self.subTest(path=relative):
                self.assertFalse(is_ignored_document(ROOT / "docs" / relative))
        self.assertTrue(
            is_ignored_document(
                ROOT / "docs/development-workspace/archive/old-docs/example.md"
            )
        )

    def test_date_check_skips_legacy_but_still_checks_managed_docs(self) -> None:
        legacy = "docs/development-workspace/archive/old-docs/legacy.md"
        managed = "docs/development-workspace/archive/archive-index.md"
        with (
            patch("docsys.evidence._git_text") as git_text,
            patch("docsys.evidence._today", return_value="2026-11-17"),
        ):
            git_text.side_effect = [legacy + "\n"]
            self.assertEqual(check_last_edited_staged(), 0)
            self.assertEqual(git_text.call_count, 1)

            git_text.reset_mock(side_effect=True)
            git_text.side_effect = [
                legacy + "\n" + managed + "\n",
                "last_edited: 2020-01-01\n",
            ]
            self.assertEqual(check_last_edited_staged(), 1)
            git_text.assert_called_with(["show", f":{managed}"])

    def test_date_sync_never_rewrites_archived_snapshots(self) -> None:
        legacy = "docs/development-workspace/archive/old-docs/legacy.md"
        with (
            patch("docsys.evidence._git_text", return_value=legacy + "\n"),
            patch("docsys.evidence._set_last_edited") as set_date,
        ):
            self.assertEqual(sync_last_edited_staged(), 0)
        set_date.assert_not_called()


if __name__ == "__main__":
    unittest.main()
