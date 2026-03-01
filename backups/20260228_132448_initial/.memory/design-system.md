# Design System — UI 디자인 규칙

## Apple-Inspired 원칙 (절대 변경 금지)
- 유리질 블러 네비게이션 (glassmorphism)
- Ken Burns 히어로 애니메이션
- rounded-2xl/3xl 카드 시스템
- 검정 배경 + 흰 글씨 네비 CTA 버튼
- 라이트 테마 기본 (다크 테마 X)

## Color Palette

| 용도 | 색상 | Hex |
|------|------|-----|
| Primary text | 거의 검정 | `#1d1d1f` |
| Secondary text | 중회색 | `#86868b` |
| Body text | 진회색 | `#424245` |
| Muted text | 연회색 | `#6e6e73` |
| Primary action | 파랑 | `#0071e3` |
| Background (light) | 연회색 | `#f5f5f7` |
| Border | 연테두리 | `#d2d2d7` |
| Divider border | 매우 연함 | `#d1d1d6` |

## CSS Utility Classes (globals.css)
```css
.btn-primary  .btn-secondary  .card  .badge
.badge-hot    .badge-pt       .badge-open
.input        .textarea       .label
.board-list-item  .tips-card  .korea-card  .testimonial-card
.skeleton
```
→ 새 스타일 추가 전 기존 클래스 먼저 사용

## Community Board Layouts

| 레이아웃 | 사용 보드 | 특징 |
|---------|---------|------|
| `list` | visa, support, support_kr | 심플 목록, accent bar |
| `hero-cards` | about | 통계 + 아이콘 카드 |
| `card-grid` | tips | 컬러바 + 이모지 카드 |
| `photo-cards` | korea | 도시 이미지 + 지도 링크 |
| `testimonial` | testimonials | 아바타 + 인용문 카드 |

## Board Badge Colors

| Board | Badge Class |
|-------|-------------|
| about | `bg-violet-50 text-violet-700 border-violet-200` |
| korea | `bg-rose-50 text-rose-700 border-rose-200` |
| visa | `bg-emerald-50 text-emerald-700 border-emerald-200` |
| support | `bg-blue-50 text-blue-700 border-blue-200` |
| support_kr | `bg-orange-50 text-orange-700 border-orange-200` |
| tips | `bg-amber-50 text-amber-700 border-amber-200` |
| testimonials | `bg-sky-50 text-sky-700 border-sky-200` |

## Framer Motion (animations.ts)
- `fadeInUp` — 아래에서 위로 페이드
- `staggerContainer` — 자식 순차 등장
- `scaleIn` — 확대 등장
- `slideInLeft` / `slideInRight` — 좌우 슬라이드
- `defaultViewport` — `{ once: true, amount: 0.3 }`

## Form UX Components
- `Dropdown` — 5+ 옵션 (select)
- `CheckList` — 다중 선택 (checkbox)
- `SingleTog` — 2-4 옵션 (토글 버튼)
- `FileUpload` — 파일 업로드 + 미리보기
- 3-Step Wizard 패턴: `step` state → StepIndicator 공통

## 간소화 이력 (2026-02-28)
- `[board]/page.tsx`: 425줄 → 275줄 (-35%)
  - `BoardHeader` 공통 컴포넌트 추출
  - `stripMd()` 유틸리티 추출 (3곳 중복 제거)
  - `accentHex()` 헬퍼 추출
- `NewPostForm.tsx`: 다크 테마 → 라이트 테마 통일
