---
name: korean-ux
description: 한국 웹 UX/UI 규칙
---

# 한국 웹 UX 규칙

## 언어 정책
- 공개 페이지 (/, /jobs, /apply, /community): 영어 기본 (외국인 교사 대상)
- 관리자 페이지 (/admin/*): 한국어 UI
- 에러 메시지: 공개=영어, 관리자=한국어
- API 응답 message: 한국어 허용 (관리자용), 공개 API는 영어

## 날짜/시간
- 표시: `ko-KR` 로케일 (`toLocaleDateString('ko-KR')`)
- 저장: UTC ISO 8601
- 관리자용: 연월일 + 시분 표시

## 전화번호
- 한국: 010-XXXX-XXXX 형식
- 국제: +82 형식도 허용

## 폼 UX
- 3-Step Wizard 패턴 (apply, inquiry)
- Enter 키 조기 제출 방지: `type="button"` + `onClick`
- 필수 필드 시각적 표시 (* 또는 빨간 테두리)
- maxLength 모든 입력에 명시

## 반응형
- Mobile-first: 공개 페이지
- Desktop-first: 관리자 페이지
- 브레이크포인트: md(768px), lg(1024px)

## 접근성
- 한국어 ARIA 라벨 (관리자)
- 영어 ARIA 라벨 (공개)
- 색상 대비 4.5:1 이상
