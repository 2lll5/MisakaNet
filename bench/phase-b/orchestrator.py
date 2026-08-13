#!/usr/bin/env python3
"""Stable Phase B entry point backed by the repository benchmark runner."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.bench_orchestrator import main


if __name__ == "__main__":
    main()
