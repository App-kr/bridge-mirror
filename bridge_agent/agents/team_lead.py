"""Team Lead agent — analyzes requests and delegates to sub-agents."""

from bridge_agent.llm.base import LLMProvider
from bridge_agent.tools.base import BaseTool
from bridge_agent.memory.loader import build_context
from bridge_agent.skills.loader import load_all_skills

from .base import BaseAgent

TEAM_LEAD_PROMPT = """# Team Lead — Bridge Base 개발팀 리더

## 역할
프로젝트 현황을 파악하고 팀원에게 작업을 분배한다.
기존 완성 기능(게시판 7개, 접수폼, Contact) 재구현은 금지.
추가/보강/버그픽스만 지시한다.

## 팀원
- **security-check**: 보안 점검 전문 (AES-256, Rate limit, XSS 방어)
- **feature-dev**: 기능 추가/보강 전문 (기존 코드 보존하며 확장)
- **qa-test**: QA 테스트 전문 (read-only, 테스트와 보고만)

## 위임 방법
작업을 팀원에게 위임할 때는 다음 형식을 사용:
```
DELEGATE:agent-name: 구체적인 작업 내용
```
예시:
```
DELEGATE:security-check: PII 필드 암호화 상태 점검
DELEGATE:feature-dev: 관리자 대시보드에 통계 차트 추가
DELEGATE:qa-test: 전체 API 엔드포인트 응답 코드 검증
```

## 규칙
- 직접 작업도 가능하지만, 전문 영역은 팀원에게 위임
- 여러 팀원에게 동시 위임 가능
- 팀원 결과를 받아 통합 보고
- 기존 완성 기능을 재구현하지 않는다
- f-string SQL 금지 — 파라미터 바인딩만
- 물리 DELETE 금지 — soft-delete만
"""


def create_team_lead(provider: LLMProvider, tools: list[BaseTool], **kwargs) -> BaseAgent:
    """Create a Team Lead agent."""
    context = build_context()
    skills = load_all_skills()
    skills_text = "\n\n".join(f"## Skill: {k}\n{v}" for k, v in skills.items())

    full_prompt = f"{TEAM_LEAD_PROMPT}\n\n{context}\n\n{skills_text}"

    return BaseAgent(
        name="team-lead",
        description="Bridge Base 개발팀 리더. 작업 분배 및 통합 검증.",
        system_prompt=full_prompt,
        provider=provider,
        tools=tools,
        **kwargs,
    )
