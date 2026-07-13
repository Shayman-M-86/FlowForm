"""FlowForm documentation tooling package (``docsys``).

A small, mostly dependency-free toolkit that treats the ``docs/`` tree as a
queryable knowledge network. It is organised as many focused, deterministic
tools rather than one large AI-driven system:

- ``model``      shared front-matter parser, document model, and glob matching
- ``gitutil``    thin wrappers over ``git`` for diffs and commit ranges
- ``index``      builds ``docs/90-generated/documentation-index.json``
- ``impact``     maps git changes onto documents via ``related_code``
- ``freshness``  classifies documents against ``verified_against_commit``
- ``query``      deterministic ranked search over the index
- ``context``    assembles the smallest useful context for a task
- ``health``     documentation health report and dashboard generators
- ``propose``    scaffolds reviewable, agent-assisted update proposals
- ``cli``        a single ``python3 -m docsys`` entry point over the above

The design keeps deterministic tooling first; AI is only ever used by callers
(agents, the MCP server) for interpretation and summarisation, never inside the
core tools. See ``docs/00-overview/documentation-model.md`` for the conventions
these tools enforce, and ``scripts/docs/docsys/README.md`` for usage.
"""

__all__ = [
    "model",
    "gitutil",
    "index",
    "impact",
    "freshness",
    "query",
    "context",
    "health",
    "propose",
]
