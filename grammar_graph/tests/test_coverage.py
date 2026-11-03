from pathlib import Path
import yaml

P = Path(__file__).resolve().parents[1] / "docs" / "HIGH_SCHOOL_GRAMMAR_COVERAGE.yaml"
LEVELS = {"core", "advanced", "csat", "error_review", "integrated"}
GRADES = {"고1", "고2", "고3"}


def test_coverage_fields_and_values():
    rows = yaml.safe_load(P.read_text(encoding="utf-8"))["coverage"]
    assert rows
    for r in rows:
        assert r["grade"] in GRADES
        assert r["coverage_level"] in LEVELS
        assert r["grammar_category"] and r["question_target"] and r["source_evidence"]


def test_coverage_no_duplicate_grade_category():
    rows = yaml.safe_load(P.read_text(encoding="utf-8"))["coverage"]
    keys = [(r["grade"], r["grammar_category"]) for r in rows]
    assert len(keys) == len(set(keys))
