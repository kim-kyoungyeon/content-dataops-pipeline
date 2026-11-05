import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import validate  # noqa: E402


def test_yaml_error_message_has_line_and_hint(tmp_path):
    p = tmp_path / "verb.tense.yaml"
    p.write_text("items:\n  - id: a\n    explanation: 해석: 나는 간다\n", encoding="utf-8")
    try:
        validate.load_yaml(p)
    except validate.yaml.YAMLError as e:
        msg = validate.yaml_error_message(p, e)
    assert msg.startswith("verb.tense.yaml:3")
    assert "따옴표" in msg


def test_style_warnings_long_and_multiline():
    items = [
        {"id": "a", "explanation": "짧은 해설"},
        {"id": "b", "explanation": "가" * 81},
        {"id": "c", "explanation": "첫 줄\n둘째 줄"},
        {"id": "d", "explanation": "  "},
    ]
    w = validate.style_warnings(Path("x.yaml"), items)
    assert len(w) == 3
    assert not any(" a:" in m or "[0]" in m for m in w)
