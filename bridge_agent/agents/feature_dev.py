"""Feature Dev agent — feature addition/enhancement specialist."""

from bridge_agent.llm.base import LLMProvider
from bridge_agent.tools.base import BaseTool
from bridge_agent.memory.loader import build_context
from bridge_agent.skills.loader import load_skill

from .base import BaseAgent

FEATURE_DEV_PROMPT = """# Feature Dev Agent — 기능 추가/보강 전문

## 역할
기존 완성 기능에 새 기능을 추가하거나 UI를 보강한다.
전면 수정/리팩토링 금지. 새 파일 추가 또는 최소 수정만.

## 규칙
1. 기존 완성 기능 재구현 금지
2. globals.css, layout.tsx, tailwind.config.* 직접 수정 금지
3. CSS 추가 필요 시 custom.css 새 파일로만
4. security_vault.py 수정 금지
5. 폼: type="button" + onClick (form onSubmit 금지)
6. DB: busy_timeout=5000, row_factory=sqlite3.Row, try/finally conn.close()
7. 응답: ok(data=..., message="...") / err("메시지", status_code)
8. 새 POST → _rate_ok(), 새 Admin → _check_admin() 필수
9. 타입: ?. nullable 체크, as any 금지
10. 수정 전 .bak 백업 → 성공 후 삭제

## 작업 흐름
1. 요청 분석 → 영향 범위 파악
2. 기존 코드 읽기 (변경할 파일만)
3. .bak 백업 생성
4. 최소 수정 구현
5. npm run build / py_compile 확인
6. curl로 동작 검증
7. 완료 보고

## 코딩 스타일
- FastAPI: 라우터 기반, 응답 래퍼(ok/err), 타입 힌팅
- Next.js: App Router, 서버 컴포넌트 기본, 'use client' 최소화
- Apple-inspired UI: 깔끔한 white/gray, 미니멀 디자인
"""


def create_feature_dev(provider: LLMProvider, tools: list[BaseTool], **kwargs) -> BaseAgent:
    """Create a Feature Dev agent."""
    context = build_context()
    code_skill = load_skill("code-style")
    design_skill = load_skill("design")
    skill_text = ""
    if code_skill:
        skill_text += f"\n\n## Code Style Skill\n{code_skill}"
    if design_skill:
        skill_text += f"\n\n## Design Skill\n{design_skill}"

    full_prompt = f"{FEATURE_DEV_PROMPT}\n\n{context}{skill_text}"

    return BaseAgent(
        name="feature-dev",
        description="기능 추가/보강 전문. 기존 코드 보존하며 확장.",
        system_prompt=full_prompt,
        provider=provider,
        tools=tools,
        **kwargs,
    )
