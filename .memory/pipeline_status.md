# Bridge Data Pipeline 현황 (2026-03-05)

## 데이터 흐름
Google Form → Sheet "Form" 시트 → Apps Script → "New" 시트
→ google_sheets_puller.py (5분 폴링) → intake CSV
→ build_candidates_db.py (수동) → master.db candidates

## 적재 현황
- Form → New → DB: 42건 Active (P0 오염 복구 완료)
- Source → DB: 3,015건 Inactive (OLD CSV 적재)
- 구인자: 953건 (149건 폼 + 804건 memo)
- Jobs: 1,066건
- 총 candidates: 3,057건

## P0~P2 완료
- P0: Active 42건 6개 필드 오염 복구
- P1: OLD/NEW CSV 자동 분기
- P2: 14개 확장 필드 매핑

## 향후 개선 (급하지 않음)
1. build_candidates_db.py 자동 실행 (puller 후 자동 트리거)
2. 804건 memo_extract에서 salary/housing/schedule 구조화 파싱
3. jobs 테이블 빈값 보강 (class_size 11%, vacation 17%)
4. Source 시트 실시간 동기화 (현재는 일괄 CSV로 충분)
5. /api/apply 웹폼 접수 → 즉시 DB INSERT (이미 구현됨, 정상)

## DB 빈값 요약

### client_inquiries (953건)
- 충실(90%+): school_name, email, phone, location, memo
- 빈값 심각(~15%): start_date, teaching_age, salary_raw, housing 등 → 804건 memo_extract 그룹
- 미사용(0%): gmail_message_id, raw_email_body, parsed_data, notes, assigned_to

### candidates (3,057건)
- 충실(85%+): full_name, nationality, email, dob, current_location, start_date
- 빈값 주의(30~50%): gender, ancestry, employment, passport, criminal_record
- 신규 전용(~1.4%): education_level, major, health_info 등 42건 Active에만
- 미사용(0%): 배치 관련, 이메일 발송, photo_url

### jobs (1,066건)
- 대부분 충실(90%+)
- 빈값 주의: district(28%), class_size(11%), vacation(17%), housing(46%)

## 주의
- build_candidates_db.py 실행 시 NEW CSV는 자동 감지됨
- .env 키 절대 변경 금지
