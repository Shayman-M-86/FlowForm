#!/usr/bin/env python3
"""Compatibility forwarder for agent tasks that cached the former hook path."""

from __future__ import annotations

import os
import sys
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "docs"
    / "hooks"
    / "stop_doc_impact_review.py"
)

os.execv(sys.executable, [sys.executable, str(TARGET), *sys.argv[1:]])
