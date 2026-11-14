"""Tests for the synthetic sample generator and the bundled sample file."""

import sys
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from src.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_sample as ms  # noqa: E402

SAMPLE = ROOT / "sample_data" / "sample_input.xlsx"


def _cell_values(path: Path):
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        return wb.sheetnames, [list(r) for r in wb.active.iter_rows(values_only=True)]
    finally:
        wb.close()


def test_generation_is_deterministic(tmp_path):
    a = ms.write_sample(tmp_path / "a.xlsx")
    b = ms.write_sample(tmp_path / "b.xlsx")
    assert _cell_values(a) == _cell_values(b)
    pd.testing.assert_frame_equal(ms.build_dataframe(), ms.build_dataframe())


def test_different_seed_changes_values():
    assert not ms.build_dataframe(seed=1).equals(ms.build_dataframe())


def test_schema_matches_expected_columns():
    sheets, rows = _cell_values(SAMPLE)
    assert sheets == ["Sheet1"]
    assert rows[0] == ms.COLUMNS
    assert len(rows) == 1 + 20


@pytest.mark.parametrize("rate,grade", [
    (130, "A"), (100, "A"), (99, "B"), (80, "B"),
    (79, "C"), (60, "C"), (59, "D"), (0, "D"),
])
def test_grade_rule_boundaries(rate, grade):
    assert ms.grade_from_rate(rate) == grade


def test_sample_grades_follow_rule():
    df = pd.read_excel(SAMPLE)
    for rate, grade in zip(df["등급판단 데이터"], df["등급"]):
        assert grade == ms.grade_from_rate(int(rate))


def test_committed_sample_matches_generator(tmp_path):
    fresh = ms.write_sample(tmp_path / "fresh.xlsx")
    assert _cell_values(SAMPLE) == _cell_values(fresh)


def test_mismatch_is_detected(tmp_path):
    """A single changed cell must make the committed-vs-generated check fail."""
    tampered = tmp_path / "tampered.xlsx"
    wb = openpyxl.load_workbook(SAMPLE)
    wb.active["C2"] = "Z"
    wb.save(tampered)
    assert _cell_values(tampered) != _cell_values(ms.write_sample(tmp_path / "f.xlsx"))


def test_pipeline_runs_on_sample(tmp_path):
    result = run_pipeline(str(SAMPLE), output_dir=str(tmp_path), verbose=False)
    assert result.success
    total = result.final_stats["total_rows"]
    flagged = result.final_stats["flagged_rows"]
    assert total == 20
    assert 0 < flagged < total

    autofill = next(s for s in result.stages if s.name == "autofill")
    assert autofill.stats["filled"] >= 1
    standardize = next(s for s in result.stages if s.name == "standardize")
    assert standardize.stats["changed"] >= 1

    flag_counts = next(s for s in result.stages if s.name == "flag").stats["flag_counts"]
    for name in ("OK", "EMPTY_DE", "WEAK_E", "AMBIG", "ATTACH",
                 "LAW_FIX", "NUM_FIX", "AI_FILLED", "ETC"):
        assert flag_counts[name] >= 1, name


def test_range_example_is_not_empty(tmp_path):
    result = run_pipeline(
        str(SAMPLE), output_dir=str(tmp_path), item_range=("1-1", "1-3"), verbose=False
    )
    assert result.success
    assert 0 < result.final_stats["total_rows"] < 20
    assert result.final_stats["flagged_rows"] >= 1
