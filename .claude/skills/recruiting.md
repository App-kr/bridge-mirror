---
name: recruiting
description: ESL 교사 채용 도메인 지식
---

# BRIDGE 채용 도메인

## 서비스 개요
- bridgejob.co.kr — 한국 내 ESL(영어) 교사 채용 플랫폼
- 대상: 외국인 교사 (지원자) + 한국 학원/학교 (구인처)
- 주요 흐름: 지원 접수 → 검토 → 면접 → 채용

## 지원자 (Candidates)
- 주요 필드: full_name, email, nationality, current_location, area_prefs, e_visa, certification
- 소스 채널: website, google_form, email, manual, import
- 상태 워크플로우: `new → reviewed → contacted → interview → hired / rejected`

## 구인처 (Client Inquiries)
- 주요 필드: school_name, contact_name, email, phone, location, vacancies, teaching_age, salary_raw
- 상태: `pending → matched → filled / cancelled`

## 인터뷰 시스템
- Google Meet 링크 자동 생성
- 이메일 자동 발송 (영어: 후보자용, 한국어: 고용주용)
- 상태: `scheduled → completed / cancelled / no_show`

## 통합 수신함 (Inbox)
- candidates + client_inquiries 통합 목록
- 소스 필터 (website/google_form/email/inquiry)
- 벌크 상태 변경, 담당자 배정, 관리자 메모
- Gmail 자동 수집 (gmail_collector.py)

## 결제
- Ad Post 게시 시 결제 (Stripe placeholder)
- 상태: pending → confirmed

## 커뮤니티 게시판
- 보드: jobs, tips, life, market, events
- 기능: pin, soft-delete, 관리자 CRUD
