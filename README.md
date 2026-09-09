# Agent Orchestration Study Example

`Building Applications with AI Agents` 5장(오케스트레이션)을 발표와 실습으로
이해하기 위한, 의존성 없는 Python 예제입니다.

이 저장소는 실제 LLM 서비스가 아닙니다. LLM, DB, 외부 API 자리에 작은 로컬
함수를 두어 **오케스트레이터가 무엇을 판단하고 어떤 순서로 실행하는지**를 눈으로
확인하게 만든 개념 모형입니다.

## 실행

Python 3.10 이상에서 추가 설치 없이 실행됩니다.

```bash
python3 agent_orchestration_study_example.py
```

발표 중 한 개념만 시연하려면 아래처럼 실행합니다.

```bash
python3 agent_orchestration_study_example.py --section reflex
python3 agent_orchestration_study_example.py --section parallel
python3 agent_orchestration_study_example.py --section graph
python3 agent_orchestration_study_example.py --section context
```

## 이 코드가 보여 주는 것

| 코드 | 책의 내용 | 발표에서 볼 장면 |
| --- | --- | --- |
| `reflex_agent` | 5.1.1 반사형 에이전트 | 조건이 맞으면 계획 없이 도구를 즉시 실행한다. |
| `semantic_tool_selection` | 5.2.2 시맨틱 선택 | 많은 도구 중 관련 후보를 먼저 줄인다. |
| `hierarchical_tool_selection` | 5.2.3 계층적 선택 | 그룹을 고른 뒤, 그룹 내부에서 세부 도구를 고른다. |
| `parallel_tool_execution` | 5.4.2 병렬 실행 | 서로 의존하지 않는 조회를 동시에 시작한다. |
| `chain_workflow` | 5.4.3 체인 | 앞 단계의 결과가 다음 단계의 입력이 된다. |
| `graph_workflow` | 5.4.4 그래프 | 상태를 들고 분기하고, 마지막에 다시 합친다. |
| `build_context` | 5.5 컨텍스트 엔지니어링 | 모델 호출 전에 필요한 정보만 골라 정해진 구조로 넣는다. |

## 발표 때 꼭 말할 정확한 구분

모델이 외부 서비스를 직접 실행하는 것이 아닙니다. 모델은 필요하다면
`tool_call` 요청을 만들고, 애플리케이션 런타임 또는 오케스트레이터가 권한,
입력 검증, 타임아웃, 재시도 정책 아래에서 실제 도구를 실행합니다.

이 예제의 `semantic_tool_selection`은 실제 임베딩 검색이 아닙니다. 도구 설명과
질문의 단어 겹침 점수를 출력해, "후보를 검색한 뒤 선택한다"는 구조만 투명하게
보여 줍니다. 실제 서비스에서는 보통 임베딩, 벡터 검색, 메타데이터 필터를 사용합니다.

## 자료

- [발표자용 상세 가이드](PRESENTATION_GUIDE.md)
- [스터디원 배포용 읽기 스크립트](STUDY_MEMBER_SCRIPT.md)
- [자동 검증 테스트](test_study_example.py)
