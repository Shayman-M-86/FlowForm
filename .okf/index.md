---
okf_version: "0.1"
---

# FlowForm knowledge bundle

FlowForm is a survey platform: creators build adaptive, versioned surveys in
**Studio**, publish them, and respondents complete them on the
**Public Site**; a Flask **backend** serves both over a single OpenAPI
contract. See the root [CLAUDE.md](../CLAUDE.md) for the full guide.

# Core workflow

```text
Create project → Create survey → Build draft version → Add questions and
conditional rules → Publish immutable version → Share public link →
Collect responses → Review submissions in Studio
```

# Architecture

* [Architecture decisions](architecture/index.md) - two-database privacy model, survey versioning, OpenAPI contract, auth, CI

# Backend

* [Backend layers](backend/index.md) - Flask API from HTTP boundary to persistence

# Frontend

* [Apps](apps/index.md) - Studio (admin dashboard) and Public Site (marketing + form filler)
* [Shared packages](packages/index.md) - `@flowform/ui`, `@flowform/styles`, `@flowform/site-shell`, `@flowform/builder`

# Tooling

* [Developer tooling](tools/index.md) - project-local MCP servers for OpenAPI discovery and repo summarisation
