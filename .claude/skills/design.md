---
name: design
description: Apple-inspired 디자인 불변 원칙
---

# BRIDGE Design System

## 불변 원칙 (Apple-inspired)

### 절대 변경 금지 영역
- 홈페이지 히어로 섹션 (Ken Burns 애니메이션)
- 글로벌 네비게이션 (유리질 블러)
- 실시간 카운터 레이아웃
- 잡보드 카드 그리드

### 색상 팔레트 (라이트 테마)
| 용도 | 값 |
|------|-----|
| 본문 텍스트 | `#1d1d1f` |
| 보조 텍스트 | `#86868b` |
| 액센트 블루 | `#0071e3` |
| 배경 그레이 | `#f5f5f7` |

### 카드 스타일
- `rounded-2xl` / `rounded-3xl`
- 미세 shadow + border
- Admin: `.card` 유틸리티 클래스 사용

### 네비 CTA 버튼
- 검정 배경 (`#1d1d1f`) + 흰 글씨
- rounded-full, hover 시 `#424245`

### Admin 영역
- 배경: `bg-[#f5f5f7]`
- max-w-7xl, 적절한 padding
- AdminNav: grid 카드형 탭 네비게이션
