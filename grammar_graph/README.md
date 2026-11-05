# Grammar Graph

[← 레포 루트 README](../README.md)

영어 문법 선수학습 그래프(DAG)를 YAML로 정의하고, GitHub Actions로 스키마·순환·도달성·문항 태그 정합성을 자동 검증하는 콘텐츠 데이터 파이프라인.

로드맵 그래프: [docs/roadmap.md](docs/roadmap.md) (GitHub에서 Mermaid로 렌더링)

## 구조

```
graph/grammar.yaml        # 노드 38개, 간선 54개 (단일 진실 공급원)
schema/*.schema.json      # 그래프, 문항 스키마
items/<node_id>.yaml      # 노드별 문항 (파일명 = 노드 ID)
docs/decisions/           # 설계 결정 기록(ADR)
docs/design-principles.md # 설계 가설(검증 전)
tools/validate.py         # 구조 검증 + Mermaid 로드맵 생성
docs/roadmap.md           # 자동 생성, 직접 수정 금지 (CI가 최신 여부 검사)
```

## 설계 결정과 가설

결정(accepted)은 [ADR](docs/decisions/)에, 아직 검증하지 않은 가설(proposed)은 [설계 원칙](docs/design-principles.md)에 둔다. 가설은 검증되면 ADR로 옮기고 status를 바꾼다. 형식은 CI(`tools/check_adr.py`)가 검사한다.

| 구분 | 문서 | 한 줄 요약 |
|---|---|---|
| 결정(accepted) | [0001](docs/decisions/0001-two-modules.md) | QA 파이프라인과 grammar_graph를 한 레포의 두 모듈로 둔다 |
| 결정(accepted) | [0002](docs/decisions/0002-graph-as-yaml-dag.md) | 선수학습 그래프를 YAML DAG로 관리한다 |
| 결정(accepted) | [0003](docs/decisions/0003-tense-as-own-node.md) | 시제를 독립 노드로 둔다 |
| 결정(accepted) | [0004](docs/decisions/0004-content-sources.md) | 문항 출처 규칙(직접 제작, 승인된 synthetic만) |
| 결정(accepted) | [0005](docs/decisions/0005-target-learner.md) | 대상은 내신·수능 중하위권 학습자 |
| 가설(proposed) | [0006~0011](docs/design-principles.md) | 진도 숨김, 표현을 바꾼 반복, 짧은 노드와 간격 반복, 오답 시 템플릿 카드, 암기/확장 단계, 집중력 신호 감지 |

문항 검수 절차는 [docs/review-flow.md](docs/review-flow.md)에 있다.

## 문항의 템플릿 연결

문항은 선택 필드 `template_id`로 설명 템플릿(정석, 단순화, 도식)과 연결할 수 있다. 소문자, 숫자, `_`, `.`, `-`만 쓴다. 아직 필수는 아니다(프로토타입 2에서 오답 카드와 함께 사용).

## 검증은 두 층으로 나눈다

| 층 | 누가 | 무엇을 |
|---|---|---|
| 구조 검증 | CI (자동) | 스키마, 중복 ID, 존재하지 않는 노드, `prereq` 순환, 루트에서 도달 불가, 문항-노드 태그 불일치, 승인자 없는 승인, 로드맵 갱신 누락 |
| 도메인 검증 | 사람 (교사) | 선수관계가 교육적으로 맞는가, 숨은 개념 순환, 문항 정답·해설의 정확성 |

구조 검증이 통과해도 내용은 틀릴 수 있다. 설계 과정에서 실제로 있었던 예: "that 판별" 노드가 관계사절 판별을 포함하면서 관계사 노드보다 앞에 있었다. 간선상으로는 순환이 없어 테스트는 통과했지만, 개념상 서로 의존하는 순환이었다. 노드를 둘로 나눠 해결했다 (`conj.that_noun` → `rel.basic` → `rel.that_exception`).

## 간선 타입

- `prereq`: 먼저 배워야 함. 순환 검사 대상.
- `related`: 참조 연결 (예: 가주어 it → to부정사). 선수관계 아님.
- `tag`: 태그 노드 부착 (특수구문: 도치, 강조, 부정).

## 문항 출처 규칙

- `source: self` 직접 제작, `source: synthetic` LLM 생성.
- synthetic 문항은 `review.status: approved` + 검수자 기록 후에만 사용.
- 고용주 자료나 시판 교재의 문항·변형 문항은 넣지 않는다.

## 문항·해설 편집 규칙

- 해설(`explanation`)은 한 줄, 80자 이내를 권장한다. 넘으면 검증기가 `WARN`으로 알려 준다(실패는 아님).
- 해설에 `: `(콜론+공백)이 들어가면 값 전체를 따옴표로 감싼다. 빠지면 YAML이 깨져 CI가 실패하고, 오류 메시지에 파일:줄이 나온다.
- GitHub 웹에서 고친 뒤에는 CI가 초록불인지 확인하고 머지한다.

## 실행

```
cd grammar_graph
pip install -r requirements.txt
python tools/validate.py --mermaid   # 검증 + 로드맵 재생성
python tools/validate.py --check     # CI와 같은 검사
python tools/check_adr.py           # ADR, 가설 문서 형식 검사 (docs/decisions, docs/design-principles.md)
pytest -q
```

## 로드맵

- 프로토타입 1: 그래프 전체 + 동사 체인 3개 노드(3단 변화, 시제, 자동사/타동사) 콘텐츠, CI, 로드맵 시각화
- 프로토타입 2: 컨테이너 이미지(GHCR), 나머지 가지 콘텐츠, 특수구문 태그, LLM 자동 노드 태깅
