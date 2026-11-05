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


HYP_RE = re.compile(r"^H-(\d{4})\.")
LINK_RE = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
RANGE_RE = re.compile(r"H-(\d{4})~H-(\d{4})")


def hypothesis_numbers(docs: Path) -> list[int]:
    p = docs / "design-principles.md"
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8")
    nums = []
    for part in re.split(r"^##\s+", text, flags=re.MULTILINE)[1:]:
        m = HYP_RE.match(part.splitlines()[0].strip())
        if m:
            nums.append(int(m.group(1)))
    return nums


def principles_errors(docs: Path) -> list[str]:
    """Only '## H-NNNN. title' headings are hypotheses. Other '##' headings
    (shared criteria, notes, references) need no status line."""
    p = docs / "design-principles.md"
    if not p.is_file():
        return []
    errs: list[str] = []
    text = p.read_text(encoding="utf-8")
    parts = re.split(r"^##\s+", text, flags=re.MULTILINE)[1:]
    for part in parts:
        title = part.splitlines()[0].strip()
        if not HYP_RE.match(title):
            continue
        statuses = STATUS_RE.findall(part)
        if not statuses:
            errs.append(f"{p.name}: '{title}': missing 'status:' line")
        elif len(statuses) > 1:
            errs.append(f"{p.name}: '{title}': more than one 'status:' line")
        for st in statuses:
            if st not in ALLOWED:
                errs.append(f"{p.name}: '{title}': invalid status '{st}'")
    nums = hypothesis_numbers(docs)
    for n in sorted({n for n in nums if nums.count(n) > 1}):
        errs.append(f"{p.name}: duplicate hypothesis number H-{n:04d}")
    if nums:
        missing = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        if missing:
            errs.append(f"{p.name}: hypothesis numbers not contiguous, missing: "
                        + ", ".join(f"H-{n:04d}" for n in missing))
    return errs


def link_errors(docs: Path) -> list[str]:
    """Relative markdown links in docs/ and the module README must resolve."""
    files = sorted(docs.rglob("*.md"))
    readme = docs.parent / "README.md"
    if readme.is_file():
        files.append(readme)
    errs: list[str] = []
    for f in files:
        for target in LINK_RE.findall(f.read_text(encoding="utf-8")):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            if not (f.parent / target).exists():
                errs.append(f"{f.name}: broken link '{target}'")
    return errs


def readme_errors(docs: Path) -> list[str]:
    """The README hypothesis range (H-NNNN~H-NNNN) must match the document."""
    readme = docs.parent / "README.md"
    nums = hypothesis_numbers(docs)
    if not readme.is_file() or not nums:
        return []
    m = RANGE_RE.search(readme.read_text(encoding="utf-8"))
    want = (min(nums), max(nums))
    if not m:
        return [f"README.md: hypothesis range 'H-{want[0]:04d}~H-{want[1]:04d}' not found"]
    got = (int(m.group(1)), int(m.group(2)))
    if got != want:
        return [f"README.md: hypothesis range H-{got[0]:04d}~H-{got[1]:04d} "
                f"does not match document H-{want[0]:04d}~H-{want[1]:04d}"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=Path, default=DOCS)
    a = ap.parse_args()
    errs = (adr_errors(a.docs) + principles_errors(a.docs)
            + link_errors(a.docs) + readme_errors(a.docs))
    for e in errs:
        print(f"ERROR {e}")
    n = len(list((a.docs / "decisions").glob("*.md")))
    print(f"adr: {n} files")
    print("FAIL" if errs else "OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
