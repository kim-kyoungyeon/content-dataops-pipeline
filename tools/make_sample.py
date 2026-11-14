#!/usr/bin/env python3
"""Generate the bundled synthetic sample: sample_data/sample_input.xlsx.

Every value in the generated sheet is synthetic. City names, ordinance
names, clause wording, reference values, correction values and grades are
invented here. They do not quote any real ordinance and do not follow any
real institution's or company's grading standard.

Grade rule (this project's own example rule):
    rate = round(measured / reference * 100)   # stored in "등급판단 데이터"
    A: rate >= 100, B: rate >= 80, C: rate >= 60, D: rate < 60

"measured" and "reference" are synthetic numbers drawn from a
fixed-seed RNG, so the output is deterministic.

Each row follows one scenario so that the sample exercises every pipeline
path: OK labels and their spacing variants (standardize), empty D/E,
weak E, ambiguous, attachment, law change, numeric change ("a->b" and
keyword), free-text ETC, and autofill from the AI column.

Usage:
    python tools/make_sample.py            # writes sample_data/sample_input.xlsx
    python tools/make_sample.py -o out.xlsx
"""

import argparse
import random
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

SEED = 20261114
SHEET_NAME = "Sheet1"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "sample_data" / "sample_input.xlsx"

COLUMNS = [
    "도시명", "항목명", "등급", "이상유무 및 수정값", "조항내용",
    "등급판단 데이터", "법령명", "조항내용.1", "이유", "광역데이터여부", "json",
]

# Fictional cities (not real municipalities).
CITIES = ["가람시", "누리시", "다솜시", "라온시"]

# (item id + name, unit, limit direction, reference value range) -- all synthetic.
ITEMS = [
    ("1-1 경사도 상한", "도", "이하", (10, 25)),
    ("1-2 건축물 높이", "m", "이하", (12, 40)),
    ("1-3 최소 대지면적", "㎡", "이상", (60, 200)),
    ("1-4 건폐율", "%", "이하", (40, 70)),
    ("1-5 용적률", "%", "이하", (150, 300)),
]

# One scenario per row (row = city_index * 5 + item_index).
SCENARIOS = [
    "ok", "empty", "ok_spaced", "ambig", "autofill",
    "ok", "num_arrow", "empty", "ok_normal", "weak_e",
    "ok", "attach", "ok_spaced", "num_keyword", "autofill",
    "ok", "law_fix", "empty", "etc", "ambig_spaced",
]

STATUS = {
    "ok": "이상없음",
    "ok_spaced": "이상 없음",
    "ok_normal": "정상",
    "ambig": "확인요",
    "ambig_spaced": "확인 필요",
    "attach": "별표 참조",
    "num_keyword": "수치변경",
    "law_fix": "조례 변경",
    "etc": "담당자 메모 남김",
}

REASON = {
    "ok": "가상 기준 충족",
    "ok_spaced": "가상 기준 충족",
    "ok_normal": "가상 기준 충족",
    "ambig": "근거 조문이 둘 이상",
    "ambig_spaced": "기준값 표기가 불분명",
    "attach": "별표에 수치가 있음",
    "num_arrow": "가상 기준값 갱신",
    "num_keyword": "가상 기준값 갱신",
    "law_fix": "근거 조문 번호 변경",
    "etc": "후속 검토 예정",
}


def grade_from_rate(rate: int) -> str:
    """Map a fulfilment rate (%) to a grade using this project's rule."""
    if rate >= 100:
        return "A"
    if rate >= 80:
        return "B"
    if rate >= 60:
        return "C"
    return "D"


def _clause(article: int, item_name: str, ref: int, unit: str, direction: str) -> str:
    return f"제{article}조({item_name}) 해당 기준은 {ref}{unit} {direction}로 한다(가상 예시 조문)."


def build_rows(seed: int = SEED) -> List[Dict[str, Optional[object]]]:
    """Build the synthetic rows deterministically from ``seed``."""
    rng = random.Random(seed)
    rows: List[Dict[str, Optional[object]]] = []

    for row_no, scenario in enumerate(SCENARIOS):
        city = CITIES[row_no // len(ITEMS)]
        item, unit, direction, (lo, hi) = ITEMS[row_no % len(ITEMS)]
        item_name = item.split(" ", 1)[1]

        ref = rng.randint(lo, hi)
        measured = rng.randint(round(ref * 0.45), round(ref * 1.2))
        rate = round(measured / ref * 100)
        article = rng.randint(10, 60)

        law = f"{city} 도시계획 예시조례"
        clause = _clause(article, item_name, ref, unit, direction)

        status: Optional[str] = STATUS.get(scenario)
        content: Optional[str] = clause
        ai_content: str = clause
        reason: Optional[str] = REASON.get(scenario)

        if scenario == "num_arrow":
            new_ref = ref + rng.randint(2, 6)
            status = f"{ref}->{new_ref}"
        elif scenario in ("empty", "autofill"):
            status, content, reason = None, None, None
            if scenario == "empty":
                # Too short for autofill (< min_ai_content_length).
                ai_content = f"제{article}조 미추출"
        elif scenario == "weak_e":
            status, reason = None, None
            # Between autofill threshold (20) and min_content_length (40).
            content = f"제{article}조 {item_name} {ref}{unit} {direction}(가상)"

        rows.append({
            "도시명": city,
            "항목명": item,
            "등급": grade_from_rate(rate),
            "이상유무 및 수정값": status,
            "조항내용": content,
            "등급판단 데이터": rate,
            "법령명": law,
            "조항내용.1": ai_content,
            "이유": reason,
            "광역데이터여부": "N",
            "json": "{}",
        })

    return rows


def build_dataframe(seed: int = SEED) -> pd.DataFrame:
    """Return the synthetic sample as a DataFrame with the expected columns."""
    return pd.DataFrame(build_rows(seed), columns=COLUMNS)


def write_sample(path: Path = DEFAULT_OUTPUT, seed: int = SEED) -> Path:
    """Write the synthetic sample workbook to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    build_dataframe(seed).to_excel(path, sheet_name=SHEET_NAME, index=False)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    print(write_sample(args.output, args.seed))


if __name__ == "__main__":
    main()
