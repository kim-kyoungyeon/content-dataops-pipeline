import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_commits as c  # noqa: E402


def test_valid_titles_pass():
    assert c.title_errors([
        "feat: add grammar graph prototype",
        "fix: typo",
        "docs: add commit message rules",
        "test: cover commit title checker",
        "refactor: extract title parser",
        "ci: add commit message format check",
        "chore: ignore output directory",
    ]) == []


def test_format_violation_is_rejected():
    errs = c.title_errors(["added a feature", "feat:"])
    assert errs
    assert any("invalid format" in e for e in errs)


def test_title_longer_than_72_characters_is_rejected():
    too_long = "feat: " + ("a" * 67)
    assert len(too_long) == 73
    errs = c.title_errors([too_long])
    assert errs
    assert any("longer than 72" in e for e in errs)

    at_limit = "feat: " + ("a" * 66)
    assert len(at_limit) == 72
    assert c.title_errors([at_limit]) == []


def test_forbidden_standalone_titles_are_rejected():
    for title in ("wip", "WIP", "fix", "Fix", "수정", "update", "UPDATE"):
        errs = c.title_errors([title])
        assert errs, f"{title!r} should be rejected"
        assert any("forbidden title" in e for e in errs)


def test_merge_commits_are_excluded():
    assert c.title_errors([
        "Merge pull request #24 from kim-kyoungyeon/docs/commit-message",
        "Merge branch 'main' into ci/check-commit-messages",
    ]) == []
