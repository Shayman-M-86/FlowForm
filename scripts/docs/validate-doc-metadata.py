#!/usr/bin/env python3
"""Validate basic Markdown metadata front matter.

Metadata: title=Validate doc metadata; document_type=docs-script; status=scaffold.
Purpose: Checks docs Markdown files for required scaffold metadata fields.
Sections: discovery, validation, reporting, limitations, TODO verification.
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

from pathlib import Path
REQ=['title:','document_type:','status: scaffold','authority:','verified_against_commit:','related_code:','related_docs:']
ROOT=Path(__file__).resolve().parents[2]
fail=[]
for p in (ROOT/'docs').rglob('*.md'):
    text=p.read_text(errors='replace')
    head=text.split('---',2)[1] if text.startswith('---') and text.count('---')>=2 else ''
    missing=[r for r in REQ if r not in head]
    if missing: fail.append((p,missing))
for p,missing in fail: print(f'{p}: missing {", ".join(missing)}')
raise SystemExit(1 if fail else 0)
