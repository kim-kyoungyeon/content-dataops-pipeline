#!/usr/bin/env python3
"""Format check for commit message titles (CONTRIBUTING.md).

Reads titles from stdin, one per line. Blank lines are skipped.

usage:
  git log origin/main..HEAD --format=%s | python tools/check_commits.py
"""
from __future__ import annotations

import re
import sys

TITLE_RE = re.compile(r"^(feat|fix|docs|test|refactor|ci|chore): .+")
MAX_LEN = 72
FORBIDDEN_ASCII = frozenset({"wip", "fix", "update"})
FORBIDDEN_EXACT = frozenset({"수정"})
MERGE_PREFIXES = ("Merge pull request", "Merge branch")
# GitHub Actions pull_request test-merge subject: "Merge <40-hex-sha> into <40-hex-sha>".
ACTIONS_TEST_MERGE_RE = re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$")


def is_merge_commit(title: str) -> bool:
    if title.startswith(MERGE_PREFIXES):
        return True
    return bool(ACTIONS_TEST_MERGE_RE.match(title))


def is_forbidden(title: str) -> bool:
    if title in FORBIDDEN_EXACT:
        return True
    return title.lower() in FORBIDDEN_ASCII


def title_errors(titles: list[str]) -> list[str]:
    """Return error messages for titles that violate the commit title rules."""
    errs: list[str] = []
    for raw in titles:
        title = raw.strip()
        if not title:
            continue
        if is_merge_commit(title):
            continue
        if is_forbidden(title):
            errs.append(f"forbidden title '{title}'")
            continue
        if len(title) > MAX_LEN:
            errs.append(f"title longer than {MAX_LEN} characters: '{title}'")
        if not TITLE_RE.match(title):
            errs.append(f"invalid format: '{title}'")
    return errs


def main() -> int:
    titles = [line.strip() for line in sys.stdin if line.strip()]
    errs = title_errors(titles)
    for e in errs:
        print(f"ERROR {e}")
    print("FAIL" if errs else "OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
