#!/usr/bin/env python3
"""Render the effective PR Genius rules for a repository."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pr_genius_rules import load_rules, rules_for_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="pr-genius.yaml")
    parser.add_argument("--changed", nargs="*", default=[])
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    rules = rules_for_paths(load_rules(args.config), args.changed)
    if args.as_json:
        print(json.dumps(rules, ensure_ascii=False, indent=2))
    else:
        for rule in rules:
            print(f"[{rule.get('category', 'repo')}] {rule['id']}: {rule.get('name', rule['id'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
