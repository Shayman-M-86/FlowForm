"""Small source-positioned Markdown AST used by documentation debt analysis.

It intentionally models structural blocks rather than rendering Markdown. The
parser is deterministic and dependency-free, and preserves line ranges for
headings, prose, lists, blockquotes, tables, thematic breaks, and fenced code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_ITEM = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+(.+)$")
_FENCE = re.compile(r"^\s*(```+|~~~+)\s*([^\s`]*)")
_TABLE_DIVIDER = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")


@dataclass
class Node:
    kind: str
    start_line: int
    end_line: int
    text: str = ""
    level: int = 0
    info: str = ""
    children: list["Node"] = field(default_factory=list)


@dataclass
class MarkdownAst:
    nodes: list[Node]

    def of_kind(self, kind: str) -> list[Node]:
        return [node for node in self.nodes if node.kind == kind]


def _starts_block(lines: list[str], index: int) -> bool:
    line = lines[index]
    return bool(
        not line.strip()
        or _HEADING.match(line)
        or _LIST_ITEM.match(line)
        or _FENCE.match(line)
        or line.lstrip().startswith(">")
        or re.match(r"^\s*(?:---+|\*\*\*+|___+)\s*$", line)
        or (
            index + 1 < len(lines)
            and "|" in line
            and _TABLE_DIVIDER.match(lines[index + 1])
        )
    )


def parse_markdown(text: str) -> MarkdownAst:
    lines = text.splitlines()
    nodes: list[Node] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        fence = _FENCE.match(line)
        if fence:
            marker, info = fence.group(1), fence.group(2)
            start = index
            index += 1
            content = []
            while index < len(lines) and not lines[index].lstrip().startswith(marker):
                content.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            nodes.append(
                Node("code_block", start + 1, index, "\n".join(content), info=info)
            )
            continue

        heading = _HEADING.match(line)
        if heading:
            nodes.append(
                Node(
                    "heading",
                    index + 1,
                    index + 1,
                    heading.group(2).strip(),
                    level=len(heading.group(1)),
                )
            )
            index += 1
            continue

        if index + 1 < len(lines) and "|" in line and _TABLE_DIVIDER.match(
            lines[index + 1]
        ):
            start = index
            content = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                content.append(lines[index])
                index += 1
            nodes.append(Node("table", start + 1, index, "\n".join(content)))
            continue

        list_item = _LIST_ITEM.match(line)
        if list_item:
            start = index
            children = []
            while index < len(lines) and (match := _LIST_ITEM.match(lines[index])):
                indent = len(match.group(1).replace("\t", "    "))
                children.append(
                    Node(
                        "list_item",
                        index + 1,
                        index + 1,
                        match.group(2),
                        level=indent // 2 + 1,
                    )
                )
                index += 1
            nodes.append(
                Node(
                    "list",
                    start + 1,
                    index,
                    "\n".join(child.text for child in children),
                    children=children,
                )
            )
            continue

        if line.lstrip().startswith(">"):
            start = index
            content = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                content.append(lines[index].lstrip()[1:].lstrip())
                index += 1
            nodes.append(Node("blockquote", start + 1, index, "\n".join(content)))
            continue

        if re.match(r"^\s*(?:---+|\*\*\*+|___+)\s*$", line):
            nodes.append(Node("thematic_break", index + 1, index + 1))
            index += 1
            continue

        start = index
        content = [line]
        index += 1
        while index < len(lines) and not _starts_block(lines, index):
            content.append(lines[index])
            index += 1
        nodes.append(Node("paragraph", start + 1, index, "\n".join(content)))

    return MarkdownAst(nodes)
