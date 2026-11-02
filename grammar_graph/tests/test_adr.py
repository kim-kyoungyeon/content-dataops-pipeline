import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_adr as c  # noqa: E402

BODY = "## 배경\nx\n\n## 결정\nx\n\n## 이유\nx\n\n## 대안\nx\n"


def adr(status_line="status: accepted", extra="", title="# t"):
    return f"{title}\n\n{status_line}\n{extra}\n{BODY}"


def make(tmp_path, files: dict[str, str], principles: str | None = None) -> Path:
    d = tmp_path / "decisions"
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text, encoding="utf-8")
    if principles is not None:
        (tmp_path / "design-principles.md").write_text(principles, encoding="utf-8")
    return tmp_path


def test_real_docs_are_valid():
    assert c.adr_errors(c.DOCS) == []
    assert c.principles_errors(c.DOCS) == []


def test_valid_set(tmp_path):
    docs = make(tmp_path, {
        "0001-a.md": adr("status: superseded", "superseded by: 0002-b.md"),
        "0002-b.md": adr(),
    })
    assert c.adr_errors(docs) == []


def test_missing_status(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr(status_line="")})
    assert any("missing 'status:'" in e for e in c.adr_errors(docs))


def test_invalid_status(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr("status: done")})
    assert any("invalid status 'done'" in e for e in c.adr_errors(docs))


def test_superseded_target_missing(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr("status: superseded", "superseded by: 0009-x.md")})
    assert any("does not exist" in e for e in c.adr_errors(docs))


def test_superseded_without_target(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr("status: superseded")})
    assert any("superseded without" in e for e in c.adr_errors(docs))


def test_duplicate_number(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr(), "0001-b.md": adr()})
    assert any("duplicate ADR number 0001" in e for e in c.adr_errors(docs))


def test_gap_in_numbers(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr(), "0003-c.md": adr()})
    assert any("missing: 0002" in e for e in c.adr_errors(docs))


def test_bad_file_name(tmp_path):
    docs = make(tmp_path, {"1-a.md": adr()})
    assert any("NNNN-slug.md" in e for e in c.adr_errors(docs))


def test_missing_section(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr().replace("## 대안", "## 기타")})
    assert any("missing section '## 대안'" in e for e in c.adr_errors(docs))


def test_principles_status(tmp_path):
    docs = make(tmp_path, {"0001-a.md": adr()},
                principles=("# p\n\n## 0006. a\nstatus: proposed\n\n"
                            "## 0007. b\nstatus: maybe\n\n## 0008. c\n"))
    errs = c.principles_errors(docs)
    assert any("invalid status 'maybe'" in e for e in errs)
    assert any("0008. c" in e and "missing" in e for e in errs)
    assert len(errs) == 2
