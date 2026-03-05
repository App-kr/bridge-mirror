# Bridge Data Pipeline 현황 (2026-03-05)

## 데이터 흐름
Google Form -> Sheet "Form" 시트 -> Apps Script -> "New" 시트
-> google_sheets_puller.py (5분 폴링) -> intake CSV
-> build_candidates_db.py (수동) -> master.db candidates

## 적재 현황
- Form -> New -> DB: 42건 Active (P0 오염 복구 완료)
- Source -> DB: 3,015건 Inactive (OLD CSV 적재)
- 구인자: 953건 (149건 폼 + 804건 memo_extract)
- Jobs: 1,066건
- 총 candidates: 3,057건

## P0~P2 완료
- P0: Active 42건 6개 필드 오염 복구
- P1: OLD/NEW CSV 자동 분기
- P2: 14개 확장 필드 매핑

## 업체관리 DB 전면 정비 분석 (2026-03-05)

### client_inquiries 데이터 그룹

| 그룹 | 건수 | source_file | 특징 |
|------|------|------------|------|
| Website 폼 | 149 | BRIDGE_clients_data*.csv | 상세 필드 충실 (20+ 필드) |
| memo 추출 | 804 | memo_extract | 기본만 (school, location, phone, email, memo) |

### memo_extract 804건 구조화 필드 현황 (모두 0%)
- start_date, teaching_age, salary_raw: 0/804
- housing_type, vacation, schedule, working_hours: 0/804
- contact_name: 217/804 (27%)만 존재

### jobs 테이블에서 보강 가능 (792/804 매칭됨!)
- 매칭 키: client_inquiries.memo = jobs.internal_notes
- teaching_age: 792/792 (100%)
- salary_raw: 791/792 (100%)
- working_hours: 790/792 (100%)
- start_date: 758/792 (96%)
- benefits: 780/792 (98%)
- housing: 322/792 (41%)
- vacation: 83/792 (10%)

### memo 텍스트 패턴 분석 (804건)
- 급여 패턴 (2.3x, 270~ 등): 599건 (75%)
- 숙소 언급: 278건 (35%)
- 인원수 (N명): 261건 (32%)
- 직책 (원장/부원장 등): 284건 (35%)
- 식사 언급: 54건 (7%)

## DB 빈값 요약

### client_inquiries (953건)
- 충실(90%+): school_name, email, phone, location, memo
- 빈값 심각(~15%): start_date, teaching_age, salary_raw 등 -> 804건 memo_extract
- 미사용(0%): gmail_message_id, raw_email_body, parsed_data, notes, assigned_to

### candidates (3,057건)
- 충실(85%+): full_name, nationality, email, dob, current_location, start_date
- 빈값 주의(30~50%): gender, ancestry, employment, passport, criminal_record
- 신규 전용(~1.4%): education_level, major, health_info 등 42건 Active에만
- 미사용(0%): 배치 관련, 이메일 발송, photo_url

### jobs (1,066건)
- 대부분 충실(90%+)
- 빈값 주의: district(28%), class_size(11%), vacation(17%), housing(46%)

## 향후 작업
1. **P3: jobs->client_inquiries 필드 보강** (792건, 즉시 가능)
2. P4: memo 텍스트에서 급여/숙소/인원 구조화 파싱
3. P5: build_candidates_db.py 자동 실행
4. P6: jobs 빈값 보강 (class_size, vacation)

## 주의
- build_candidates_db.py 실행 시 NEW CSV는 자동 감지됨
- .env 키 절대 변경 금지
