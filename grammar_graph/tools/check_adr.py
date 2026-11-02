#!/usr/bin/env python3
"""Format check for ADRs (docs/decisions) and hypotheses (docs/design-principles.md).

Checks format only. Whether a decision is right is reviewed by a person.

usage:
  python tools/check_adr.py            # check docs/, exit 1 on error
  python tools/check_adr.py --docs DIR
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ALLOWED = {"proposed", "accepted", "superseded"}
REQUIRED_SECTIONS = ("배경", "결정", "이유", "대안")
NAME_RE = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
STATUS_RE = re.compile(r"^status:\s*(\S*)\s*$", re.MULTILINE)
SUPERSEDED_RE = re.compile(r"^superseded by:\s*(\S+)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def adr_errors(docs: Path) -> list[str]:
    ddir = docs / "decisions"
    if not ddir.is_dir():
        return [f"{ddir}: directory missing"]
    errs: list[str] = []
    numbers: dict[int, list[str]] = {}
    for p in sorted(ddir.glob("*.md")):
        m = NAME_RE.match(p.name)
        if not m:
            errs.append(f"{p.name}: file name must be NNNN-slug.md")
            continue
        numbers.setdefault(int(m.group(1)), []).append(p.name)
        text = p.read_text(encoding="utf-8")
        statuses = STATUS_RE.findall(text)
        if not statuses:
            errs.append(f"{p.name}: missing 'status:' line")
        elif len(statuses) > 1:
            errs.append(f"{p.name}: more than one 'status:' line")
        elif statuses[0] not in ALLOWED:
            errs.append(f"{p.name}: invalid status '{statuses[0]}' "
                        f"(allowed: {', '.join(sorted(ALLOWED))})")
        sections = set(SECTION_RE.findall(text))
        for s in REQUIRED_SECTIONS:
            if s not in sections:
                errs.append(f"{p.name}: missing section '## {s}'")
        if statuses and statuses[0] == "superseded":
            targets = SUPERSEDED_RE.findall(text)
            if not targets:
                errs.append(f"{p.name}: superseded without 'superseded by: <file>' line")
            for t in targets:
                if t == p.name:
                    errs.append(f"{p.name}: superseded by itself")
                elif not (ddir / t).is_file():
                    errs.append(f"{p.name}: superseded by '{t}' which does not exist")
    for n, names in sorted(numbers.items()):
        if len(names) > 1:
            errs.append(f"duplicate ADR number {n:04d}: {', '.join(names)}")
    if numbers:
        nums = sorted(numbers)
        expected = list(range(1, nums[-1] + 1))
        missing = sorted(set(expected) - set(nums))
        if missing:
            errs.append("ADR numbers not contiguous, missing: "
                        + ", ".join(f"{n:04d}" for n in missing))
    return errs


def principles_errors(docs: Path) -> list[str]:
    p = docs / "design-principles.md"
    if not p.is_file():
        return []
    errs: list[str] = []
    text = p.read_text(encoding="utf-8")
    # each "## " heading is one hypothesis and must carry exactly one status line
    parts = re.split(r"^##\s+", text, flags=re.MULTILINE)[1:]
    for part in parts:
        title = part.splitlines()[0].strip()
        statuses = STATUS_RE.findall(part)
        if not statuses:
            errs.append(f"{p.name}: '{title}': missing 'status:' line")
        for st in statuses:
            if st not in ALLOWED:
                errs.append(f"{p.name}: '{title}': invalid status '{st}'")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=Path, default=DOCS)
    a = ap.parse_args()
    errs = adr_errors(a.docs) + principles_errors(a.docs)
    for e in errs:
        print(f"ERROR {e}")
    n = len(list((a.docs / "decisions").glob("*.md")))
    print(f"adr: {n} files")
    print("FAIL" if errs else "OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
