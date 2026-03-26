# Quick Start

```bash
git clone https://github.com/Shayman-M-86/FlowForm.git
cd FlowForm
code .vscode/flowform.code-workspace
```

## Setup

Allow automatic tasks when prompted.

If it doesn’t run:

* Press `Ctrl + Shift + B` to run `Build Task`

---

## Package Management

This project uses uv for dependency management.

* Do not use `pip` directly
* Use `uv` commands for installing and syncing dependencies

[UV Python package manager](https://github.com/astral-sh/uv)

---

## Workspace

This is a **multi-root workspace**:

* `root` → entire repository
* `backend` → backend only
* `frontend` → frontend only

You can:

* Work from **root** for the full project
* Work from **backend** if focusing on API development

---

## Recommended Extensions

* ms-python.python
* ms-python.vscode-pylance
* charliermarsh.ruff
* ms-python.black-formatter

---

### Note

If tasks were blocked:

`Ctrl + Shift + P` → `Tasks: Manage Automatic Tasks` → Allow
