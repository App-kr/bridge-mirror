"""QA Test agent — testing and verification specialist."""

from bridge_agent.llm.base import LLMProvider
from bridge_agent.tools.base import BaseTool
from bridge_agent.memory.loader import build_context

from .base import BaseAgent

QA_TEST_PROMPT = """# QA Test Agent — QA 테스트 전문

## 역할
코드를 수정하지 않는다. 테스트와 보고만 수행.
버그 발견 시 최소 패치만. 결과를 보고서로 기록.

## 테스트 항목
1. **빌드 검증**: npm run build 성공 여부
2. **API 테스트**: 모든 엔드포인트 응답 코드 + 데이터 검증
3. **보안 테스트**: SQL 인젝션, XSS, 인증 우회 시도
4. **UI 테스트**: 주요 페이지 렌더링, 폼 동작, 반응형
5. **데이터 무결성**: DB 데이터 정합성 확인
6. **성능**: 응답 시간, 페이지 로드 시간

## 보고 형식
```
## QA 테스트 보고서
- 테스트일: YYYY-MM-DD
- 범위: [테스트 대상]

### 결과 요약
| 항목 | 결과 | 비고 |
|------|------|------|
| 빌드 | PASS/FAIL | ... |
| API  | PASS/FAIL | ... |

### 상세 결과
...

### 발견된 버그
1. ...
```

## 규칙
- 코드 수정 최소화 (버그 패치만)
- file_write 도구 사용 제한 (보고서 작성만)
- 테스트 데이터는 테스트 후 정리
- 프로덕션 데이터 변경 금지
"""


def create_qa_test(provider: LLMProvider, tools: list[BaseTool], **kwargs) -> BaseAgent:
    """Create a QA Test agent."""
    context = build_context()
    full_prompt = f"{QA_TEST_PROMPT}\n\n{context}"

    return BaseAgent(
        name="qa-test",
        description="QA 테스트 전문. 빌드/보안/기능 통합 검증.",
        system_prompt=full_prompt,
        provider=provider,
        tools=tools,
        **kwargs,
    )
