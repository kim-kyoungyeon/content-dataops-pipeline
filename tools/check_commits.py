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
# Exempt only the exact subjects that git and GitHub generate, so that a
# hand-written title starting with "Merge" cannot bypass the format check.
MERGE_RES = (
    # GitHub merge button: "Merge pull request #24 from owner/branch"
    re.compile(r"^Merge pull request #\d+ from \S+$"),
    # git merge: "Merge branch 'main'", "... of <url>", "... into <branch>"
    re.compile(r"^Merge branch '[^']+'( of \S+)?( into \S+)?$"),
    re.compile(r"^Merge remote-tracking branch '[^']+'( into \S+)?$"),
    # GitHub Actions pull_request test-merge: "Merge <sha> into <sha>"
    re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$"),
)


def is_merge_commit(title: str) -> bool:
    return any(r.match(title) for r in MERGE_RES)


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
