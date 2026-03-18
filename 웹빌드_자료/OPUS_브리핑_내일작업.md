# BRIDGE 자동화 — Opus 작업 브리핑
> 작성: 2026-03-17 | Sonnet 준비 → 내일 Opus 실행

---

## 작업 목표
1. **Google Apps Script** — 구글폼 제출 시 New 시트 자동 처리
2. **5자리 번호 자동 부여** — 10001부터 시작
3. **프로필 메일 빌더** — admin/mail-send에 후보자 선택 → HTML 자동 생성

---

## 구글 시트 구조 (실제 확인)

**스프레드시트 ID**: `1PveCbB7yfPhsmV-YwERf2PjoaKtXJmB0uJngu1dhTxM`

### 탭 이름 (하단 탭 순서)
1. **New** — 운영 관리 시트 (메인)
2. **Client** — 업체/구인자 목록
3. **Source** — 구글폼 원본 데이터 (form 시트)
4. **Form** — (용도 확인 필요)
5. 정리24, 정리25, Note, 선물 — 기타

### New 시트 구조
- **헤더**: 1행 + 2행 (총 2행 헤더)
- **데이터 시작**: 3행부터
- **현재 최고 번호**: 5583
- **5자리 번호 시작**: 10001
- **컬럼 순서** (왼쪽→오른쪽):
  ```
  A(1):  이메일 주소 / 메
  B(2):  Full name / 이름
  C(3):  Photo / 사진 (수동)
  D(4):  No / 번호 ← 자동부여
  E(5):  ARC holders
  F(6):  Nationality / 국적
  G(7):  Family Ancestry Background / 배경
  H(8):  Date of Birth / 나이
  I(9):  Gender / 성별
  J(10): Current Location / 현재
  K(11): Start date / 시작
  L(12): Target / 대상
  M(13): Area prefs / 지역
  N(14): Reference / 레퍼런스/근무처확인
  O(15): Experience / 경력
  P(16): Employment / 한국
  Q(17): Job prefs / 선호사항/리크루터인터뷰
  R(18): Interview / 지원한곳/인터뷰요청 (수동)
  S(19): Apply / 포지션제안/진행 (수동)
  T(20): Current salary / 현급
  U(21): Desired salary / 희망
  V(22): Interview time / 시간
  W(23): Degree / 학위
  X(24): Major / 전공
  Y(25): Certification / 자격
  Z(26): Documents / 서류
  AA(27): Health Information / 건강
  AB(28): Personal Considerations / 타투
  AC(29): piercings / 피어
  AD(30): Dependents Pets / 가족
  AE(31): Marital Status / 결혼
  AF(32): Housing / 숙소
  AG(33): Religion / 종교
  AH(34): E visa / 비자
  AI(35): KakaoTalk / 카톡
  AJ(36): Mobile Phone / 핸폰 (PII — 관리자 내부)
  AK(37): Criminal Record / 범죄
  AL(38): Criminal Record in Korea / 국범
  AM(39): Agreement / 동의
  AN(40): Facts / 사실
  AO(41): How to / 경로
  AP(42): 타임스탬프
  AQ(43): 채용처 (수동)
  AR(44): 임금 (수동)
  AS(45): 개시월 (수동)
  AT(46): 숙박 (수동)
  AU(47): 비용 (수동)
  AV(48): 처리 (수동)
  AW(49): 과거메모 (수동)
  ```
- **상단 진행메모**: 행 합치기로 만든 메모 영역
  - 형식: `업체코드 S번호` (예: `두X S5569`, `대치DEP S5513`)
  - S = Seoul? 또는 Status 표시자
- **색상 구분**:
  - 녹색 배경 = 채용 진행 중 (상단)
  - 노란 배경 = 신규 접수
  - 흰색 = 일반 대기

### Source 시트 구조 (구글폼 원본)
컬럼 순서 (1-indexed):
```
1: 타임스탬프
2: 이메일 주소
3: How to (경로)
4: Attach your files (첨부)
5: Full name
6: Nationality
7: Family Ancestry Background
8: Date of Birth
9: Gender
10: Current Location
11: Educational Background
12: Major
13: Certification
14: E visa
15: Passport
16: Criminal Record
17: Document Status
18: Start date
19: Target
20: Area prefs
21: Job prefs (Notes)
22: Employment (한국 경력)
23: Reference
24: Current salary
25: Desired salary
26: Marital Status
27: Dependents Pets
28: Housing
29: Personal Considerations
30: Religion
31: Health Information
32: Criminal Record in Korea
33: Interview time
34: KakaoTalk
35: Mobile Phone
36: Agreement
37: Facts
38: 메모
```

---

## 자동화 규칙

### 번호 부여
- 현재 4자리 (1000~5583 혼용) → 신규는 10001부터 5자리
- New 시트 D열에서 max() 찾아서 +1
- 기존 4자리는 그대로 유지

### New 시트 자동 매핑 (Source → New)
```
Source col → New col
이메일(2)  → 메(A)
Full name(5) → 이(B)
[번호 자동] → 번(D)
Start date(18) → 시(F)
Target(19) → 대(G)
Area prefs(20) → 지(H)
Reference(23) → 레퍼런스
Job prefs(21) → 선호사항/리크루터인터뷰
Current salary(24) → 현급
Desired salary(25) → 희망
E visa(14) → 비자
KakaoTalk(34) → 카톡
Educational Background(11) → 학위
Major(12) → 전공
Certification(13) → 자격
Document Status(17) → 서류
Criminal Record(16) → 범죄
Passport(15) → 만료
Agreement(36) → 정보
Facts(37) → 사실
How to(3) → 경로
Interview time(33) → 시간
Employment(22) → 한국/경력
Nationality(6) → 국적
Gender(9) → 성별
Date of Birth(8) → 나이
Current Location(10) → 현재
```

### 삽입 위치
- 3행 위에 새 행 삽입 (상단 메모 행들 아래, 데이터 최상단)
- 신규 접수 배경색: 연노랑 `#FFFDE7`
- 아래 행의 서식 복사 (conditional formatting 유지)

---

## 프로필 메일 형식 (02.JPG 기준)

### 이메일 구조
```
제목: BRIDGE 원어민 강사 소식! 국내/해외 프로필 확인하세요

본문:
[강사 프로필 블록 반복 (1~99명)]

■{번호}{국적flag} {국내/해외}거주{이모지}
[사진]
•선호지역 자격 기타: {지역} | {비자} | {기타}
•경력 주거 희망급여: {경력}년 | {숙소} | {희망급여}
•리크루터 인터뷰: {인터뷰내용}
•레퍼런스: {레퍼런스}
[희망사항] {희망사항} (노란 형광 배경)
[기피사항] {기피사항} (노란 형광 배경)
•타깃 근로개시: {시작일}

[서명 + QR코드 + 법적고지]
```

### 국적 → 국기 이모지 매핑
```
미국 → 🇺🇸
캐나다 → 🇨🇦
영국 → 🇬🇧
남아공 → 🇿🇦
뉴질랜드 → 🇳🇿
호주 → 🇦🇺
아일랜드 → 🇮🇪
```

---

## 업체 관리 (DOCX → DB)

### 현재 DOCX 구조 (테스트용_정리.docx)
각 업체당 두 블록:
1. **내부용** (괄호 안): 실제 업체명, 담당자 연락처, 내부 메모
2. **발송용**: `[도시] / Job. XXXX / Starting Date / Teaching Age / ...`

### Job 코드 체계
- `Job. 1003` — 부산
- `Job. 1204` — 서울 구로
- `Job. 3879` — 용인

---

## Opus 내일 작업 순서

### Step 1: Google Apps Script (30분)
파일: Google Sheets → 확장 프로그램 → Apps Script
```
1. onFormSubmit 트리거 설정
2. Source 시트 마지막 행 읽기
3. New 시트에 매핑된 데이터 삽입 (3행 위)
4. 5자리 번호 자동 부여
5. 신규 접수 색상 표시
6. 완료 로그
```

### Step 2: 메일 빌더 UI (1시간)
파일: `web_frontend/src/app/admin/mail-send/page.tsx`
```
1. "프로필 빌더" 탭 추가
2. 후보자 번호 입력 or 목록에서 선택
3. 02.JPG 형태 HTML 자동 생성
4. 기존 mail-send 본문에 자동 삽입
```

### Step 3: 검증 및 테스트 (30분)
```
1. 폼 테스트 제출 → New 시트 확인
2. 번호 부여 확인
3. 메일 HTML 생성 확인
4. 빌드 통과 확인
5. git push
```

---

## 참고 파일 위치
- 테스트 샘플: `Q:\Claudework\bridge base\웹빌드_자료\`
- 이력서 샘플: `1053미국_여성(89born).pdf`, `1057미국_여성(94born).pdf`
- 발송 메일 샘플: `02.JPG`, `03.JPG`
- 업체 정리 샘플: `테스트용_정리.docx`
- 접수 스프레드시트 샘플: `테스트용_지원자접수.xlsx`

---

## 주의사항 (CLAUDE.md 핵심)
- 비밀번호 변경 절대 금지
- hard-delete 금지 → is_deleted=1
- SQL f-string 삽입 금지 (parameterized query만)
- 작업 전 git backup 필수
- PII: 관리자 패널=전체표시 / 공개API=완전마스킹
