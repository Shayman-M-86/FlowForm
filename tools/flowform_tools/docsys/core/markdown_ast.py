"""Small source-positioned Markdown AST used by documentation debt analysis.

It intentionally models structural blocks rather than rendering Markdown. The
parser is deterministic and dependency-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .model import HEADING_RE

_LIST_ITEM = re.compile(r"^(\s*)(?:[-+*]|\d+[.)])\s+(.+)$")
_FENCE = re.compile(r"^\s*(```+|~~~+)\s*([^\s`]*)")
_TABLE_DIVIDER = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")


@dataclass
class Node:
    kind: str
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
        or HEADING_RE.match(line)
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
            index += 1
            content = []
            while index < len(lines) and not lines[index].lstrip().startswith(marker):
                content.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            nodes.append(Node("code_block", "\n".join(content), info=info))
            continue

        heading = HEADING_RE.match(line)
        if heading:
            nodes.append(
                Node(
                    "heading",
                    heading.group(2).strip(),
                    level=len(heading.group(1)),
                )
            )
            index += 1
            continue

        if index + 1 < len(lines) and "|" in line and _TABLE_DIVIDER.match(
            lines[index + 1]
        ):
            content = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                content.append(lines[index])
                index += 1
            nodes.append(Node("table", "\n".join(content)))
            continue

        list_item = _LIST_ITEM.match(line)
        if list_item:
            children = []
            while index < len(lines) and (match := _LIST_ITEM.match(lines[index])):
                indent = len(match.group(1).replace("\t", "    "))
                children.append(
                    Node(
                        "list_item",
                        match.group(2),
                        level=indent // 2 + 1,
                    )
                )
                index += 1
            nodes.append(
                Node(
                    "list",
                    "\n".join(child.text for child in children),
                    children=children,
                )
            )
            continue

        if line.lstrip().startswith(">"):
            content = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                content.append(lines[index].lstrip()[1:].lstrip())
                index += 1
            nodes.append(Node("blockquote", "\n".join(content)))
            continue

        if re.match(r"^\s*(?:---+|\*\*\*+|___+)\s*$", line):
            nodes.append(Node("thematic_break"))
            index += 1
            continue

        content = [line]
        index += 1
        while index < len(lines) and not _starts_block(lines, index):
            content.append(lines[index])
            index += 1
        nodes.append(Node("paragraph", "\n".join(content)))

    return MarkdownAst(nodes)
