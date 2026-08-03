from __future__ import annotations

import unittest

from flowform_tools.docsys.contracts import (
    FindRequest,
    ReadRequest,
    execute_find,
    execute_read,
)
from flowform_tools.docsys.model import DOCS, ROOT, DocSet, Document


def _doc(
    name: str,
    *,
    title: str,
    status: str = "draft",
    body: str = "",
    related_code: tuple[str, ...] = (),
) -> Document:
    path = DOCS / "project-knowledge" / f"{name}.md"
    return Document(
        path=path,
        rel_path=path.relative_to(ROOT).as_posix(),
        docs_dir=DOCS,
        front_matter={
            "title": title,
            "aliases": [],
            "document_type": "overview",
            "status": status,
            "authority": "canonical",
            "tags": [],
            "related_docs": [],
            "related_code": list(related_code),
        },
        body=body,
        headings=[
            line.lstrip("#").strip()
            for line in body.splitlines()
            if line.startswith("#")
        ],
        related_patterns=list(related_code),
    )


class DiscoveryContractTests(unittest.TestCase):
    def test_find_is_bounded_and_ranks_relevance_before_status(self) -> None:
        docs = [
            _doc(
                "draft-title",
                title="Alpha",
                body="# Alpha\n\nDirect title match.",
            ),
            _doc(
                "verified-body",
                title="Other",
                status="verified",
                body="# Other\n\nAlpha appears only in the body.",
            ),
            *[
                _doc(
                    f"extra-{index}",
                    title=f"Extra {index}",
                    body=f"# Extra {index}\n\nAlpha body match.",
                )
                for index in range(3)
            ],
        ]

        response = execute_find(FindRequest(query="alpha"), DocSet(docs))

        self.assertEqual(response.returned, 3)
        self.assertEqual(response.total, 5)
        self.assertTrue(response.truncated)
        self.assertEqual(response.items[0].path, docs[0].rel_path)
        self.assertNotIn("score", response.items[0].as_dict())

    def test_match_modes_and_exact_code_filter_are_explicit(self) -> None:
        code_path = "tools/flowform_tools/docsys/model.py"
        docs = [
            _doc(
                "both",
                title="Alpha Beta",
                body="# Alpha Beta\n\nCombined.",
                related_code=(code_path,),
            ),
            _doc("one", title="Alpha", body="# Alpha\n\nOnly one term."),
        ]
        docset = DocSet(docs)

        all_matches = execute_find(
            FindRequest(query="alpha beta", match="all"),
            docset,
        )
        any_matches = execute_find(
            FindRequest(query="alpha beta", match="any"),
            docset,
        )
        phrase_matches = execute_find(
            FindRequest(query="alpha beta", match="phrase"),
            docset,
        )
        code_matches = execute_find(
            FindRequest(code_paths=(code_path,)),
            docset,
        )

        self.assertEqual(all_matches.total, 1)
        self.assertEqual(any_matches.total, 2)
        self.assertEqual(phrase_matches.total, 1)
        self.assertEqual(code_matches.items[0].path, docs[0].rel_path)
        with self.assertRaisesRegex(ValueError, "exact file"):
            FindRequest(code_paths=("tools/flowform_tools/docsys",))

    def test_read_is_exact_outline_first_and_bounded(self) -> None:
        doc = _doc(
            "read-me",
            title="Read me",
            body=(
                "# Read me\n\nIntroduction.\n\n"
                "## Details\n\nA deliberately longer section body.\n\n"
                "## Next\n\nDone.\n"
            ),
        )
        docset = DocSet([doc])

        outline = execute_read(ReadRequest(path=doc.rel_path), docset)
        section = execute_read(
            ReadRequest(
                path=doc.rel_path,
                section="Details",
                max_chars=20,
            ),
            docset,
        )

        self.assertIsNone(outline.content)
        self.assertEqual(outline.headings, ("Read me", "Details", "Next"))
        self.assertTrue(section.truncated)
        self.assertEqual(section.next_offset, 20)
        self.assertEqual(len(section.content or ""), 20)
        self.assertEqual(section.start_line, 5)
        self.assertEqual(section.end_line, 7)
        with self.assertRaisesRegex(ValueError, "document not found"):
            execute_read(ReadRequest(path="docs/missing.md"), docset)

    def test_read_reports_repository_source_lines_after_front_matter(self) -> None:
        doc = _doc(
            "source-lines",
            title="Source lines",
            body="\n# Source lines\n\nIntro.\n\n## Details\n\nEvidence.\n",
        )
        doc.body_start_line = 10

        response = execute_read(
            ReadRequest(path=doc.rel_path, section="Details"),
            DocSet([doc]),
        )

        self.assertEqual(response.content, "## Details\n\nEvidence.")
        self.assertEqual(response.start_line, 15)
        self.assertEqual(response.end_line, 17)


if __name__ == "__main__":
    unittest.main()
