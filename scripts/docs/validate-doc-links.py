#!/usr/bin/env python3
"""Validate local Markdown links in docs.

Metadata: title=Validate doc links; document_type=docs-script; status=scaffold.
Purpose: Finds relative Markdown links that do not resolve to files or directories.
Sections: discovery, parsing, resolution, reporting, TODO verification.
TODO: Verify this against the current implementation.
"""

# Section: Purpose
# This script provides basic documentation validation without third-party dependencies.
# TODO: Verify this against the current implementation.
# Section: Inputs
# The script reads Markdown files under docs/ and reports issues to standard output.
# TODO: Verify this against the current implementation.
# Section: Outputs
# The script exits with status 0 for success and 1 when validation issues are found.
# TODO: Verify this against the current implementation.
# Section: Limitations
# This scaffold intentionally performs simple checks and should be expanded only with verified needs.
# TODO: Verify this against the current implementation.

import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
fail=[]
pat=re.compile(r'\[[^\]]+\]\(([^)]+)\)')
for p in (ROOT/'docs').rglob('*.md'):
    for link in pat.findall(p.read_text(errors='replace')):
        if '://' in link or link.startswith('#') or link.startswith('mailto:'): continue
        target=(p.parent/link.split('#')[0]).resolve()
        if link.split('#')[0] and not target.exists(): fail.append((p,link))
for p,l in fail: print(f'{p}: broken link {l}')
raise SystemExit(1 if fail else 0)
