# content-dataops-pipeline

영어 문법 선수학습 그래프(DAG)를 YAML로 정의하고, GitHub Actions로 스키마·순환·도달성·문항 태그 정합성을 자동 검증하는 콘텐츠 데이터 파이프라인.

로드맵 그래프: [docs/roadmap.md](docs/roadmap.md) (GitHub에서 Mermaid로 렌더링)

## 구조

```
graph/grammar.yaml        # 노드 38개, 간선 54개 (단일 진실 공급원)
schema/*.schema.json      # 그래프, 문항 스키마
items/<node_id>.yaml      # 노드별 문항 (파일명 = 노드 ID)
tools/validate.py         # 구조 검증 + Mermaid 로드맵 생성
docs/roadmap.md           # 자동 생성, 직접 수정 금지 (CI가 최신 여부 검사)
```

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

## 실행

```
pip install -r requirements.txt
cd grammar_graph && python tools/validate.py --mermaid   # 검증 + 로드맵 재생성
pytest -q
```

## 로드맵

- 프로토타입 1: 그래프 전체 + 동사 체인 3개 노드(3단 변화, 시제, 자동사/타동사) 콘텐츠, CI, 로드맵 시각화
- 프로토타입 2: 컨테이너 이미지(GHCR), 나머지 가지 콘텐츠, 특수구문 태그, LLM 자동 노드 태깅
