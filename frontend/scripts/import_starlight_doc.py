#!/usr/bin/env python3

from __future__ import annotations

import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
except ImportError:
    DND_FILES = None
    TkinterDnD = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "frontend/apps/public-site/src/content/docs/docs"
ASTRO_CONFIG_PATH = REPO_ROOT / "frontend/apps/public-site/astro.config.mjs"
SIDEBAR_SECTION_LABEL = "Getting Started"


def slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized.strip("-")


def parse_drop_path(raw_value: str) -> str:
    value = raw_value.strip().strip('"')
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1]
    if value.startswith("file://"):
        value = value[7:]
    return value


def normalize_source_path(raw_value: str) -> Path:
    value = parse_drop_path(raw_value)
    windows_path = re.match(r"^([A-Za-z]):[\\/](.*)$", value)
    if windows_path:
        drive = windows_path.group(1).lower()
        rest = windows_path.group(2).replace("\\", "/")
        value = f"/mnt/{drive}/{rest}"
    return Path(value).expanduser()


def extract_title(content: str) -> str | None:
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
    if frontmatter_match:
        title_match = re.search(r"^title:\s*(.+?)\s*$", frontmatter_match.group(1), re.MULTILINE)
        if title_match:
            return title_match.group(1).strip().strip("\"'")

    heading_match = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()

    return None


def split_frontmatter(content: str) -> tuple[list[str], str]:
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
    if not frontmatter_match:
        return [], content
    return frontmatter_match.group(1).splitlines(), content[frontmatter_match.end() :]


def format_frontmatter_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,_()/-]*", value):
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def ensure_frontmatter(content: str, title: str) -> str:
    frontmatter_lines, body = split_frontmatter(content)
    has_title = False
    has_description = False
    updated_lines: list[str] = []

    for line in frontmatter_lines:
        if re.match(r"^title\s*:", line):
            updated_lines.append(f"title: {format_frontmatter_value(title)}")
            has_title = True
            continue
        if re.match(r"^description\s*:", line):
            updated_lines.append('description: ""')
            has_description = True
            continue
        updated_lines.append(line)

    if not has_title:
        updated_lines.insert(0, f"title: {format_frontmatter_value(title)}")
    if not has_description:
        insert_at = 1 if updated_lines and re.match(r"^title\s*:", updated_lines[0]) else len(updated_lines)
        updated_lines.insert(insert_at, 'description: ""')

    return "---\n" + "\n".join(updated_lines) + "\n---\n\n" + body.lstrip()


def escape_js_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def update_astro_config(title: str, slug: str) -> None:
    config_text = ASTRO_CONFIG_PATH.read_text(encoding="utf-8")
    target_slug = f"docs/{slug}"

    if re.search(rf"slug:\s*['\"]{re.escape(target_slug)}['\"]", config_text):
        return

    section_pattern = re.compile(
        rf"(\{{\s*label:\s*'{re.escape(SIDEBAR_SECTION_LABEL)}',\s*items:\s*\[)(.*?)(\]\s*,\s*\}})",
        re.DOTALL,
    )
    section_match = section_pattern.search(config_text)
    if not section_match:
        raise ValueError(f"Could not find sidebar section '{SIDEBAR_SECTION_LABEL}' in astro.config.mjs.")

    items_block = section_match.group(2)
    insertion = (
        "\n            "
        f"{{ label: '{escape_js_string(title)}', slug: '{escape_js_string(target_slug)}' }},"
    )
    updated_items_block = items_block + insertion
    updated_config = (
        config_text[: section_match.start(2)]
        + updated_items_block
        + config_text[section_match.end(2) :]
    )
    ASTRO_CONFIG_PATH.write_text(updated_config, encoding="utf-8")


def import_doc(source_path: Path, title: str, slug: str) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    destination = DOCS_DIR / f"{slug}.md"

    content = source_path.read_text(encoding="utf-8")
    content = ensure_frontmatter(content, title)
    destination.write_text(content, encoding="utf-8")
    update_astro_config(title=title, slug=slug)
    return destination


class ImportApp:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.root.title("Import Starlight Doc") # type: ignore
        self.root.geometry("640x420") # type: ignore
        self.root.minsize(640, 420) # type: ignore
        self.root.resizable(True, True) # type: ignore

        self.slug_dirty = False
        self.updating_slug_programmatically = False
        self.source_path_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.slug_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Choose a markdown file. In WSL, use Browse or Paste Path because drag-and-drop may not work."
        )

        self.build_ui()
        self.title_var.trace_add("write", self.on_title_change)
        self.slug_var.trace_add("write", self.on_slug_change)

    def build_ui(self) -> None:
        container = tk.Frame(self.root, padx=18, pady=18)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Markdown file", anchor="w", font=("TkDefaultFont", 10, "bold")).pack(fill="x")

        drop_frame = tk.Frame(container, bd=1, relief="solid", padx=12, pady=12)
        drop_frame.pack(fill="x", pady=(8, 12))

        self.drop_label = tk.Label(
            drop_frame,
            text="Drag and drop an .md file here, or click Browse.",
            anchor="w",
            justify="left",
        )
        self.drop_label.pack(fill="x")

        path_row = tk.Frame(container)
        path_row.pack(fill="x", pady=(0, 12))

        path_entry = tk.Entry(path_row, textvariable=self.source_path_var)
        path_entry.pack(side="left", fill="x", expand=True)

        tk.Button(path_row, text="Browse", command=self.browse_file).pack(side="left", padx=(8, 0))
        tk.Button(path_row, text="Paste Path", command=self.paste_path).pack(side="left", padx=(8, 0))

        tk.Label(container, text="Title", anchor="w", font=("TkDefaultFont", 10, "bold")).pack(fill="x")
        tk.Entry(container, textvariable=self.title_var).pack(fill="x", pady=(8, 12))

        tk.Label(container, text="Slug", anchor="w", font=("TkDefaultFont", 10, "bold")).pack(fill="x")
        tk.Entry(container, textvariable=self.slug_var).pack(fill="x", pady=(8, 12))

        tk.Label(
            container,
            text="The slug is saved lowercase and uses dashes for spaces.",
            anchor="w",
            fg="#666666",
        ).pack(fill="x")

        actions = tk.Frame(container)
        actions.pack(fill="x", pady=(18, 10))

        tk.Button(actions, text="Import Doc", command=self.run_import).pack(side="left")
        tk.Button(actions, text="Quit", command=self.root.destroy).pack(side="right")

        tk.Label(container, textvariable=self.status_var, anchor="w", justify="left", wraplength=580).pack(fill="x")

        if DND_FILES and hasattr(drop_frame, "drop_target_register"):
            drop_frame.drop_target_register(DND_FILES) # type: ignore
            drop_frame.dnd_bind("<<Drop>>", self.handle_drop) # type: ignore

    def browse_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose markdown file",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if selected:
            self.set_source_path(selected)

    def handle_drop(self, event: tk.Event) -> None:
        dropped = parse_drop_path(event.data) # type: ignore
        self.set_source_path(dropped)

    def paste_path(self) -> None:
        try:
            clipboard_text = self.root.clipboard_get()
        except tk.TclError:
            self.status_var.set("Clipboard does not contain text.")
            return
        self.set_source_path(clipboard_text)

    def set_source_path(self, raw_path: str) -> None:
        path = normalize_source_path(raw_path)
        self.source_path_var.set(str(path))
        if path.suffix.lower() != ".md":
            self.status_var.set("Please choose a markdown (.md) file.")
            return
        if not path.exists():
            self.status_var.set("That file does not exist.")
            return

        content = path.read_text(encoding="utf-8")
        guessed_title = extract_title(content) or path.stem.replace("-", " ").replace("_", " ").title()
        self.slug_dirty = False
        self.title_var.set(guessed_title)
        self.status_var.set("File loaded. Review the title and slug, then click Import Doc.")

    def on_title_change(self, *_args: object) -> None:
        if self.slug_dirty:
            return
        self.updating_slug_programmatically = True
        self.slug_var.set(slugify(self.title_var.get()))
        self.updating_slug_programmatically = False

    def on_slug_change(self, *_args: object) -> None:
        sanitized = slugify(self.slug_var.get())
        if sanitized != self.slug_var.get():
            self.updating_slug_programmatically = True
            self.slug_var.set(sanitized)
            self.updating_slug_programmatically = False
            return
        if not self.updating_slug_programmatically:
            self.slug_dirty = bool(sanitized)

    def run_import(self) -> None:
        raw_source = self.source_path_var.get().strip()
        title = self.title_var.get().strip()
        slug = slugify(self.slug_var.get().strip() or title)

        if not raw_source:
            messagebox.showerror("Missing file", "Choose a markdown file first.")
            return
        if not title:
            messagebox.showerror("Missing title", "Enter a title before importing.")
            return
        if not slug:
            messagebox.showerror("Missing slug", "Enter a valid slug before importing.")
            return

        source_path = Path(raw_source).expanduser()
        if source_path.suffix.lower() != ".md" or not source_path.exists():
            messagebox.showerror("Invalid file", "Choose an existing markdown (.md) file.")
            return

        try:
            destination = import_doc(source_path=source_path, title=title, slug=slug)
        except Exception as exc:  # pragma: no cover - UI error path
            messagebox.showerror("Import failed", str(exc))
            self.status_var.set(f"Import failed: {exc}")
            return

        self.updating_slug_programmatically = True
        self.slug_var.set(slug)
        self.updating_slug_programmatically = False
        self.status_var.set(
            f"Imported to {destination.relative_to(REPO_ROOT)} and updated astro.config.mjs."
        )
        messagebox.showinfo("Import complete", self.status_var.get())


def create_root() -> tk.Misc:
    if TkinterDnD is not None:
        return TkinterDnD.Tk()
    return tk.Tk()


def main() -> None:
    root = create_root()
    ImportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
