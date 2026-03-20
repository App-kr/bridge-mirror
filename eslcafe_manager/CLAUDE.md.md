# BRIDGE ESLCafe 광고 자동화 — Claude Code 실행 지시서

## 프로젝트 개요
BRIDGE ESLCafe 광고 자동화 데스크탑 앱을 바탕화면에 생성한다.
ESLCafe에 총 25건의 채용공고를 포함하는 광고 HTML을 자동 생성하고,
관리자가 버튼 클릭만으로 광고를 생성·복사·미리보기할 수 있어야 한다.

---

## 실행 환경
- OS: Windows 10/11
- 작업 폴더: `Q:\Claudework\bridge base\eslcafe_manager\`
- Python: `.venv\Scripts\python` (Q드라이브 내 가상환경)
- 최종 결과물: 바탕화면에 `BRIDGE_ESLCafe.html` 생성

---

## Step 1 — 폴더 구조 생성

```
Q:\Claudework\bridge base\eslcafe_manager\
├── BRIDGE_ESLCafe.html          ← 메인 앱 (단일 파일)
├── jobs\
│   └── jobs_default.json        ← 25개 기본 공고 데이터
├── exports\
│   └── (생성된 광고 html 저장)
└── logs\
    └── (생성 이력 로그)
```

바탕화면에 `BRIDGE_ESLCafe.html` 바로가기(복사본)도 생성한다.

---

## Step 2 — 25개 채용공고 데이터 (jobs_default.json)

아래 25개 공고를 `jobs_default.json`으로 저장한다.
`p: true` = 프리미엄 (방학 길거나 근무시간 짧은 공고) — 항상 최상단 3개 고정.

```json
[
  {
    "id": "2035", "l": "Seoul", "r": "seoul",
    "p": true, "h": true, "a": true,
    "sal": "2.30m-2.80m", "date": "Apr / Aug",
    "hrs": "08:30~16:30", "hsg": "Allowance 400k (no deposit)",
    "txt": "Starting Date: April, August\nTeaching Age: Elementary\nClass size: ~5~15\nWorking Hours: 08:30~16:30\nVacation: 4~5 weeks (incl. summer & winter camps)\nMonthly Salary: 2.30m-2.80m KRW\nHousing: Allowance 400k, no deposit cost\nBA in education/related field + ESL cert + 2+ yrs Korea experience + reference letter required\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation"
  },
  {
    "id": "1671", "l": "Chuncheon", "r": "etc",
    "p": true, "h": true, "a": true,
    "sal": "2.50m-3.20m", "date": "May / Sep",
    "hrs": "08:40~16:40", "hsg": "Provided or allowance",
    "txt": "Starting Date: May, September\nTeaching Age: Elementary\nWorking Hours: 08:40~16:40\nMonthly Salary: 2.50m-3.20m KRW\nVacation: 4~6 weeks\nHigh salary requires MA/PhD in education\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, vacation, contract completion bonus, airfare support"
  },
  {
    "id": "2022", "l": "Seongnam", "r": "gg",
    "p": true, "h": true, "a": true,
    "sal": "2.50m-3.20m", "date": "Jun / Sep",
    "hrs": "08:45~16:45", "hsg": "Provided or allowance",
    "txt": "Starting Date: June, September\nTeaching Age: Kindergarten\nWorking Hours: 08:45~16:45\nMonthly Salary: 2.50m-3.20m KRW\nVacation: 4~5 weeks\nPGCE holders preferred; lesson plans developed collaboratively without textbooks\nIf you have children aged 4~7, they may apply for admission\nEmployee Benefits: Visa sponsorship, severance, pension, insurance, vacation, airfare"
  },
  {
    "id": "3090", "l": "Seoul Seongdong", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-2.80m", "date": "ASAP",
    "hrs": "09:00~17:00", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: ASAP\nTeaching Age: Kindy - Elem\nClass size: ~12\nWorking Hours: 09:00~17:00\nAverage Teaching Hours/Week: 23\nMonthly Salary: 2.50m-2.80m KRW\nHousing: Provided or allowance 500k (5M deposit)\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "2968", "l": "Incheon Yeonsu", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.40m-3.20m", "date": "Jul / Sep",
    "hrs": "08:30~17:30", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: July, September\nTeaching Age: Elem - High school\nWorking Hours: 08:30~17:30\nVacation: 15~20 days\nMonthly Salary: 2.40m-3.20m KRW\nHousing: Provided or allowance 500k\nF-visa holders with BA or higher also welcome\nEmployee Benefits: Visa sponsorship, severance, pension, insurance, vacation, medical check support, airfare"
  },
  {
    "id": "2966", "l": "Suwon Gwanggyo", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-3.20m", "date": "April",
    "hrs": "09:10~18:45", "hsg": "Provided or allowance 700k",
    "txt": "Starting Date: April\nTeaching Age: Kindy - Elem\nClass size: ~12\nWorking Hours: 09:10~18:45\nMonthly Salary: 2.50m-3.20m KRW\nHousing: Provided or allowance 700k (5M deposit)\nF-visa holders with BA or higher also welcome\nEmployee Benefits: Visa sponsorship, severance, pension, insurance, vacation, renewal bonus, airfare"
  },
  {
    "id": "2662", "l": "Gyeongju", "r": "etc",
    "p": false, "h": false, "a": true,
    "sal": "2.50m", "date": "Aug / Sep",
    "hrs": "13:00~19:00", "hsg": "Provided",
    "txt": "Starting Date: August, September\nTeaching Age: Elementary\nClass size: ~8\nWorking Hours: 13:00~19:00\nMonthly Salary: 2.50m KRW\nHousing: Provided\nPrefer teachers residing in Korea with positive attitude and strong teamwork\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation"
  },
  {
    "id": "3299", "l": "Seoul Yongsan", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-3.10m", "date": "Feb / May",
    "hrs": "08:30~17:00", "hsg": "Provided or allowance 600k",
    "txt": "Starting Date: February, May\nTeaching Age: Pre-K - Kindy\nWorking Hours: 08:30~17:00\nMonthly Salary: 2.50m-3.10m KRW\nHousing: Provided or allowance 600k\nReference from most recent Korea employer mandatory\nVacation: 13~20 days + 2 week unpaid break after contract\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "3365", "l": "Yongin", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-2.80m", "date": "June",
    "hrs": "08:20~16:20", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: June\nTeaching Age: Kindy - Elem\nClass size: ~9~12\nWorking Hours: 08:20~16:20\nMonthly Salary: 2.50m-2.80m KRW\nHousing: Provided or allowance 500k\nWe prefer bright, positive, energetic teachers with excellent teamwork skills\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation"
  },
  {
    "id": "3340", "l": "Goyang", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.60m-3.00m", "date": "April",
    "hrs": "13:00~19:00", "hsg": "Provided or allowance",
    "txt": "Starting Date: April\nTeaching Age: Kindy - Elem\nClass size: ~12\nWorking Hours: 13:00~19:00\nVacation: 20 days\nMonthly Salary: 2.60m-3.00m KRW\nHousing: Provided or allowance\nPassionate teachers who are not job-hoppers preferred\nEmployee Benefits: Visa sponsorship, pension, severance pay, insurance, vacation, airfare"
  },
  {
    "id": "3217", "l": "Jeju", "r": "etc",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-2.60m", "date": "January",
    "hrs": "13:50~20:00", "hsg": "Provided or allowance 400k",
    "txt": "Starting Date: January\nTeaching Age: Elem - Middle school\nClass size: ~12\nWorking Hours: 13:50~20:00\nMonthly Salary: 2.50m-2.60m KRW\nHousing: Provided or allowance 400k\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "2897", "l": "Suwon", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.60m-3.10m", "date": "October",
    "hrs": "14:00~20:30", "hsg": "Not provided",
    "txt": "Starting Date: October\nTeaching Age: Elementary\nClass size: ~30\nWorking Hours: MWF 14:00~20:00 / TTH 14:00~20:30\nMonthly Salary: 2.60m-3.10m KRW\nF-visa native speakers preferred\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation"
  },
  {
    "id": "1027", "l": "Seoul Gangdong", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-2.80m", "date": "ASAP",
    "hrs": "07:30~16:30", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: ASAP\nTeaching Age: Elementary Grade 1\nWorking Hours: 07:30~16:30\nVacation: 4~8 weeks/year\nMonthly Salary: 2.50m~2.80m KRW\nHousing: Provided or allowance 500k\nFull-time Korea experience required, no contract breaches\nBA in Education, History, Political Science, Geography or related field preferred\nEmployee Benefits: Severance pay, pension, insurance, paid vacation"
  },
  {
    "id": "1924", "l": "Busan Gangseo", "r": "etc",
    "p": false, "h": false, "a": true,
    "sal": "2.40m-2.80m", "date": "Jan / Jul",
    "hrs": "09:00~18:00", "hsg": "Provided",
    "txt": "Starting Date: January, July\nTeaching Age: Kindy - Elem\nClass size: ~8\nWorking Hours: 09:00~18:00\nMonthly Salary: 2.40m-2.80m KRW\nHousing: Provided\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, partial airfare support"
  },
  {
    "id": "2329", "l": "Yongin", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-3.20m", "date": "Aug / Sep",
    "hrs": "09:00~18:00", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: August, September\nTeaching Age: Kindy - Elem\nWorking Hours: 09:00~18:00\nMonthly Salary: 2.50m-3.20m KRW\nHousing: Provided or allowance 500k\n3.0m+ requires education major + 2 yrs full-time experience\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, vacation, airfare"
  },
  {
    "id": "2230", "l": "Seoul Mapo", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "2.70m-3.00m", "date": "September",
    "hrs": "09:00~18:00", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: September\nTeaching Age: Kindy - Elem\nWorking Hours: 09:00~18:00\nMonthly Salary: 2.70m-3.00m KRW\nHousing: Provided or allowance 500k\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "2058", "l": "Seoul Gangdong", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-3.00m", "date": "April",
    "hrs": "09:00~18:00", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: April\nTeaching Age: Kindy - Elem\nWorking Hours: 09:00~18:00\nMonthly Salary: 2.50m-3.00m KRW\nHousing: Provided or allowance 500k (no deposit help)\n1-3 years experience + F visa holders welcome\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, vacation, lunch flex, airfare"
  },
  {
    "id": "2830", "l": "Incheon", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.40m-2.70m", "date": "November",
    "hrs": "09:00~18:00", "hsg": "Provided or allowance 400k",
    "txt": "Starting Date: November\nTeaching Age: Kindergarten\nClass size: ~12\nWorking Hours: 09:00~18:00\nMonthly Salary: 2.40m~2.70m KRW\nAverage Teaching Hours/Week: 30\nHousing: Provided or allowance 400k\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "3315", "l": "Seoul Seocho", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "2.80m-3.10m", "date": "Feb ~ May",
    "hrs": "08:00~16:30", "hsg": "Not provided",
    "txt": "Starting Date: February~May\nTeaching Age: Elementary to High School\nWorking Hours: 08:00~16:30\nVacation: 8~11 weeks\nMonthly Salary: 2.80m-3.10m KRW\nEnergetic 20s~30s with F-visa, high-level teaching ability preferred\nFrequent job changers please refrain from applying\nEmployee Benefits: Severance pay, pension, insurance (no visa/deposit support)"
  },
  {
    "id": "3383", "l": "Busan Namgu", "r": "etc",
    "p": false, "h": false, "a": true,
    "sal": "2.60m-2.80m", "date": "June",
    "hrs": "09:20~18:30", "hsg": "Provided",
    "txt": "Starting Date: June\nTeaching Age: Kindy - Elem\nWorking Hours: 09:20~18:30\nMonthly Salary: 2.60m-2.80m KRW\nHousing: Provided\nTeaching major + certification preferred\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation"
  },
  {
    "id": "2048", "l": "Seongnam", "r": "gg",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-2.80m", "date": "ASAP / Sep",
    "hrs": "09:00~18:00", "hsg": "Provided or allowance 500k",
    "txt": "Starting Date: ASAP, September\nTeaching Age: Kindy - Elem\nClass size: ~11\nAverage Teaching Hours/Week: 30\nWorking Hours: 09:00~18:00 (may leave at 5 PM when classes finish early)\nMonthly Salary: 2.50m-2.80m KRW\nHousing: Provided or allowance 500k\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "2163", "l": "Seongnam", "r": "gg",
    "p": false, "h": true, "a": true,
    "sal": "2.80m-4.30m", "date": "Jan / Sep",
    "hrs": "14:10~21:20", "hsg": "Not provided",
    "txt": "Starting Date: January, September\nTeaching Age: Elementary\nClass size: ~10\nWorking Hours: 14:10~21:20\nVacation: 12~15 days\nMonthly Salary: 2.80m-4.30m KRW\nHousing: Not provided\nHumble person with strong organizational skills preferred\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation"
  },
  {
    "id": "3110", "l": "Seoul Gangnam", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "3.00m-3.20m", "date": "July",
    "hrs": "08:30~17:00", "hsg": "Allowance 700k only",
    "txt": "Starting Date: July\nTeaching Age: Kindy - Elem\nClass size: ~12\nWorking Hours: 08:30~17:00\nVacation: 15~20 days\nMonthly Salary: 3.00m-3.20m KRW\nHousing: Allowance 700k only (no deposit)\nHigh salary requires proven teaching passion and ability — not just years\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "2015", "l": "Jeju", "r": "etc",
    "p": false, "h": false, "a": true,
    "sal": "2.50m-2.70m", "date": "Apr / Aug",
    "hrs": "08:30~17:30", "hsg": "Provided or allowance 300k",
    "txt": "Starting Date: April, August\nTeaching Age: Kindy - Elem\nWorking Hours: 08:30~17:30\nMonthly Salary: 2.50m-2.70m KRW\nHousing: Provided or allowance 300k (no deposit)\nPositive and outgoing individuals strongly encouraged\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, airfare"
  },
  {
    "id": "2570", "l": "Seoul Seodaemun", "r": "seoul",
    "p": false, "h": false, "a": true,
    "sal": "2.40m-3.00m", "date": "May / Aug",
    "hrs": "09:30~18:00", "hsg": "Provided or allowance 600k",
    "txt": "Starting Date: May, August, ASAP\nTeaching Age: Kindy - Elem\nWorking Hours: MWF 09:30~17:00 / TTH 09:30~18:00\nMonthly Salary: 2.40m-3.00m KRW\nHousing: Provided or allowance 600k (couple-friendly accommodation available)\nEmployee Benefits: Visa sponsorship, severance pay, pension, insurance, paid vacation, round-trip airfare"
  }
]
```

---

## Step 3 — 메인 앱 (`BRIDGE_ESLCafe.html`) 빌드 규칙

### 3-1. 전체 아키텍처

단일 HTML 파일. 외부 서버 불필요. 브라우저에서 직접 실행.

**화면 레이아웃 (3분할):**
```
┌─────────────────────────────────────────────────────────────────┐
│  TOPBAR: BRIDGE 로고 · 탭 · 시계 · [🎲 랜덤] [▶ 광고 생성]       │
├───────────────┬──────────────────────────┬──────────────────────┤
│  LEFT(340px)  │   CENTER(flex-1)         │   RIGHT(460px)       │
│  공고 목록    │   생성 옵션 / 편집 탭     │   미리보기 / 소스     │
│  ─────────    │   ─────────────────────  │   ─────────────────  │
│  ⭐ 프리미엄  │   [광고 생성하기 버튼]    │   iframe 실시간      │
│  🔀 랜덤      │   HTML 코드 출력          │   소스 직접편집      │
└───────────────┴──────────────────────────┴──────────────────────┘
```

### 3-2. 공고 목록 (LEFT)
- `p:true` 공고 → `⭐ 프리미엄` 섹션 상단 고정
- 나머지 → `🔀 랜덤 배치` 섹션
- 각 행: `[번호] [지역] [급여] [시간] [HOT뱃지] [활성뱃지]`
- 클릭 → 중앙 편집 탭으로 전환
- 프리미엄 공고 왼쪽에 보라색 세로선 표시
- 검색 박스 (지역명 / Job ID)
- 필터 칩: 전체 / ⭐프리미엄 / 🔥HOT / 서울 / 경기+인천 / 지방

### 3-3. 광고 생성 로직 (핵심)

**buildOrder() — 순서 결정:**
```
1. pool = 활성 공고 전체
2. prems = pool에서 p:true인 것 (최대 3개 상단 고정)
3. rest = 나머지 → Fisher-Yates 완전 랜덤 셔플
4. ordered = [...prems_pinned, ...overflow_prems, ...rest]
5. HOT 자동 부여: 프리미엄은 항상 HOT, 나머지는 25% 확률
6. jobs 배열 자체를 ordered 순서로 재정렬 → 목록도 동기화
```

**생성될 광고 HTML 구조 (이 순서 그대로):**
```
① HERO 배너 (네이비→블루 그라디언트)
   - "GOV'T-CERTIFIED AGENCY · BRIDGE"
   - "Teach English in Korea"
   - "The right school, the right support — your next chapter starts here"
   - [APPLY NOW →] 버튼
   - WHO CAN APPLY 칩 5개 (SVG 아이콘 + 텍스트)
   - 해시태그 행

② 채용 카드들 (랜덤 배치, 5개마다 Apply Bar 삽입)

③ HOW TO APPLY (4단계 플로우)
   Submit → Video Call with BRIDGE → School Interview → Start

④ WHAT YOU GET (복지 10개, 2열 그리드)

⑤ FOOTER (네이비 배경)
```

### 3-4. 카드 디자인 규칙
- 지역명: `font-weight:600; color:#111` (검정, 얇게)
- Job 번호: `font-size:20px; font-weight:600; color:#1a5ff8` (지역명과 동일 크기)
- 상단 컬러 바: 일반=파랑, 프리미엄=보라 그라디언트
- 항목: SVG 아이콘 + 텍스트 (2열 그리드)
- HOT 뱃지: 노란 배경, 진한 갈색 텍스트

### 3-5. Anti-Copy 난독화 (3단계 선택)
- L1: CSS 클래스명에 랜덤 suffix (예: `card-a3k9`)
- L2: Base64 인코딩 클래스명
- L3: CSS 전체를 base64 후 JS 런타임 주입

### 3-6. SVG 아이콘 시스템
모든 아이콘은 Heroicons 스타일 인라인 SVG. emoji 사용 금지.
stroke-width:1.7, stroke-linecap:round, fill:none

필수 아이콘 정의:
- globe, academic, doc, video, id (WHO CAN APPLY용)
- plane, home, shield, sun, key, star, grow, users, badge, academic (복지용)
- form, chat, handshake, badge (전형 절차용)

### 3-7. 우측 패널
**미리보기 탭**: `<iframe srcdoc="...">` 실시간 렌더링
**소스 탭**: `<textarea>` 직접 편집 → `✓ 적용` 버튼으로 미리보기 업데이트
→ ESLCafe Source 버튼 에러 시 소스 탭에서 수동 편집 가능

---

## Step 4 — 기능 목록

| 기능 | 설명 |
|------|------|
| 광고 생성 | 랜덤 셔플 + 프리미엄 고정 + 자동 HOT → HTML 생성 |
| ⎘ HTML 복사 | navigator.clipboard.writeText() |
| 🔗 새 탭 미리보기 | Blob URL → 새 탭 (상단에 복사 버튼 포함) |
| ⬇ .html 저장 | Blob 다운로드 → exports\ 폴더 |
| 🎲 랜덤 재배치 | shuffle() + generateAd() 동시 실행 |
| ✏️ 공고 편집 | 클릭 → 우측 편집 폼, 실시간 미리보기 |
| ＋ 공고 추가 | 빈 폼 → 저장 |
| 🗑 공고 삭제 | confirm() 후 삭제 |
| 💾 저장 | localStorage에 자동 저장 |
| 📤 JSON 내보내기 | jobs 배열 → .json 파일 |
| 📥 JSON 불러오기 | .json → jobs 배열 |
| ↺ 기본값 초기화 | DEFAULT_JOBS로 리셋 |
| URL 전환 | Google Form ↔ bridgejob.co.kr |

---

## Step 5 — 디자인 토큰

```css
--navy: #003366
--blue: #1a5ff8
--blue2: #1248c8
--green: #05b97d
--bg: #f0f2f5
--white: #ffffff
--gray1: #1a1d25   /* 본문 텍스트 */
--gray2: #3d4150
--gray3: #6b7280
--gray4: #9ca3af
--gray5: #d1d5db
--gray6: #e5e7eb
--gray7: #f3f4f6   /* 카드 배경 */
--shadow: 0 1px 4px rgba(0,0,0,.07)
--shadow2: 0 4px 16px rgba(0,0,0,.09)
--r: 8px
--r-lg: 12px
--r-xl: 16px
--f: Pretendard, -apple-system, 'Segoe UI', sans-serif
--mono: 'JetBrains Mono', monospace
```

---

## Step 6 — 보안 및 데이터 규칙

### 절대 금지 (PII 보호)
- 고용주 실명 노출 금지
- 학원·학교 실제 주소 노출 금지
- 담당자 개인 연락처 노출 금지
- 실제 업체명 노출 금지 → 지역명만 표시

### 허용 정보
- 지역명 (구 단위까지)
- Job ID (내부 관리용 번호)
- 급여 범위
- 근무 시간
- 복지 내용 (주거·비자·보험 등 일반적 항목)

---

## Step 7 — 완성 기준 체크리스트

```
[ ] Q:\Claudework\bridge base\eslcafe_manager\ 폴더 구조 생성
[ ] jobs\jobs_default.json — 25개 공고 저장
[ ] BRIDGE_ESLCafe.html — 단일 파일 완성
[ ] JS 문법 오류 없음 (script 태그 1개, 열고 닫기 균형)
[ ] 생성된 광고 HTML 안에 </script> 태그 직접 노출 없음
    (반드시 '<scr'+'ipt>' 분리 처리)
[ ] 25개 공고 전체 로드 확인
[ ] 🎲 랜덤 버튼 → 목록 + 미리보기 동시 갱신 확인
[ ] ⭐ 프리미엄 3개 항상 최상단 고정 확인
[ ] ⎘ 복사 → ESLCafe 붙여넣기 시 정상 렌더링
[ ] 바탕화면에 BRIDGE_ESLCafe.html 파일 존재
```

---

## Step 8 — 오푸스에게 전달할 최종 프롬프트

이 CLAUDE.md를 기반으로 Claude Code(Opus)에게 다음과 같이 지시한다:

```
이 CLAUDE.md의 모든 사양을 정확히 구현해서
Q:\Claudework\bridge base\eslcafe_manager\BRIDGE_ESLCafe.html
을 생성하고, 바탕화면에도 복사해줘.

핵심 요구사항:
1. 25개 공고 모두 포함 (jobs_default.json 참조)
2. 생성 버튼 클릭 → 랜덤 배치 + 프리미엄 3개 최상단 고정
3. 생성된 HTML을 ESLCafe에 그대로 붙여넣을 수 있어야 함
4. JS 문법 오류 없이 브라우저에서 바로 실행 가능
5. 광고 생성 코드 안에 </script> 직접 노출 금지
   반드시 '<scr'+'ipt>' 형태로 분리할 것
6. 모든 아이콘은 인라인 SVG (emoji 사용 금지)
7. 우측 패널에 미리보기 + 소스 편집 탭 모두 구현

작업 완료 후:
- git add . && git commit -m "feat: ESLCafe ad manager v5 complete"
- 한국어로 완료 보고 작성
```

---

## 참고: 기존 작업 파일 위치
```
현재 최신 버전: Q:\Claudework\bridge base\eslcafe_manager\bridge-eslcafe-v5.html
이 파일을 참고하되, CLAUDE.md 사양대로 완전히 새로 빌드할 것.
```

---

## Step 9 — 날짜 자동 변환 (스마트 Start Date)

### 개요
광고 생성 시점의 현재 월을 기준으로, 이미 지난 채용 시작월은 자동으로 `ASAP`으로 변환한다.

### 변환 함수 (JS — 앱 내 포함)

```javascript
var MONTHS = {
  'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
  'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12,
  'january':1,'february':2,'march':3,'april':4,'june':6,
  'july':7,'august':8,'september':9,'october':10,'november':11,'december':12
};

function smartDate(raw, nowMonth) {
  // nowMonth: 현재 월 (1~12)
  var s = (raw||'').trim();
  if (!s || s.toUpperCase() === 'ASAP') return 'ASAP';
  if (s.toLowerCase().indexOf('asap') >= 0) return s; // "ASAP / Sep" → 유지

  // " / ", ", ", "~", " ~ " 등 구분자로 파트 분리
  var parts = s.split(/\s*[\/,~&]\s*/);
  var results = [];
  parts.forEach(function(p) {
    var key = p.trim().toLowerCase().replace(/[^a-z]/g,'');
    var mNum = MONTHS[key];
    if (!mNum) { results.push(p.trim()); return; }
    results.push(mNum <= nowMonth ? 'ASAP' : p.trim());
  });

  // ASAP 중복 제거
  var seen = false;
  var clean = results.filter(function(r) {
    if (r === 'ASAP') { if (seen) return false; seen = true; return true; }
    return true;
  });
  if (clean.every(function(r){ return r === 'ASAP'; })) return 'ASAP';
  return clean.join(' / ');
}
```

### 적용 방법
광고 생성 함수 `generateAd()` 안에서 카드 렌더링 전에 적용:

```javascript
var nowMonth = new Date().getMonth() + 1; // 1~12
ordered.forEach(function(j) {
  j.displayDate = smartDate(j.date, nowMonth);
  // txt 안의 "Starting Date: ..." 줄도 변환
  j.displayTxt = j.txt.replace(
    /(Starting Date:\s*)(.+)/,
    function(_, prefix, dateStr) {
      return prefix + smartDate(dateStr, nowMonth);
    }
  );
});
```

### 변환 예시 (현재 3월 기준)

| 원본 date | 변환 결과 |
|-----------|----------|
| `January` | `ASAP` |
| `February` | `ASAP` |
| `March` | `ASAP` |
| `April` | `April` (유지) |
| `Jan / Jul` | `ASAP / Jul` |
| `Feb / May` | `ASAP / May` |
| `Feb ~ May` | `ASAP / May` |
| `Jun / Sep` | `Jun / Sep` (유지) |
| `ASAP / Sep` | `ASAP / Sep` (유지) |
| `ASAP` | `ASAP` (유지) |
| `October` | `October` (유지) |

### 주의
- `date` 필드는 원본 보존 (localStorage 저장 시 변환 전 값 유지)
- 변환은 **렌더링 시점에만** 적용 (displayDate 사용)
- 편집 폼에는 원본 date 값 표시

---

## Step 10 — Claude Code 실행 프롬프트 (오푸스용)

이 폴더(`eslcafe_manager`)에서 Claude Code 실행 후 아래 전체를 붙여넣기:

```
CLAUDE.md를 읽고 다음을 실행해줘:

1. BRIDGE_ESLCafe.html 생성
   - 위치: Q:\Claudework\bridge base\eslcafe_manager\BRIDGE_ESLCafe.html
   - 단일 HTML 파일, 외부 서버 불필요
   - 브라우저에서 바로 실행 가능

2. 구현 필수 사항:
   a) 25개 공고 데이터 전체 포함 (Step 2의 jobs_default.json 내용)
   b) 광고 생성 버튼 클릭 → 랜덤 배치 + 프리미엄 3개 최상단 고정
   c) smartDate() 함수 구현 — 현재 월 기준으로 지난 달은 ASAP 변환
   d) 카드 Starting Date 렌더링 시 smartDate() 적용
   e) HOT 배지: 프리미엄 항상 HOT, 비프리미엄은 4번째마다 자동 배정
   f) 우측 패널: 미리보기 탭(iframe) + 소스 편집 탭(textarea)
   g) APPLY NOW 버튼: display:block; width:fit-content; margin:0 auto (서브타이틀과 분리)
   h) 지원 URL: https://docs.google.com/forms/d/e/1FAIpQLSf3zwNSEb00ErLIOTLH4YwnQr4AhmzewXYG8xISgZKOpzMimg/viewform?usp=header
   i) Anti-Copy L1/L2/L3 난독화 옵션
   j) ⎘ 복사 / 🔗 새탭 미리보기 / ⬇ .html 저장 버튼

3. 디자인 토큰 (Step 5) 준수
   - 폰트: 지역명/Job번호 22px weight:600, 카드 항목 14px
   - 카드 색상 바: 일반=파랑, 프리미엄=보라 그라디언트
   - 모든 아이콘: 인라인 SVG (emoji 금지)

4. JS 품질 기준:
   - script 태그 정확히 1개 (열고 닫기 균형)
   - 생성 HTML 안에 </script> 직접 노출 금지
     반드시 '<scr'+'ipt>' 형태로 분리
   - 브라우저 콘솔 오류 없음

5. 완료 후:
   - 바탕화면에 BRIDGE_ESLCafe.html 복사
   - git add . && git commit -m "feat: BRIDGE ESLCafe ad manager complete"
   - 한국어로 완료 보고 (기능별 체크리스트 포함)
```

---

## Step 11 — 광고 생성 후 ESLCafe 게시 방법

1. `▶ 광고 생성` 버튼 클릭
2. `⎘ HTML 복사` 버튼 클릭 → 클립보드에 저장
3. ESLCafe.com → **Post a Job** 접속
4. 에디터 상단 **`Source`** 버튼 클릭
5. 기존 내용 전체 선택 후 `Ctrl+V`
6. **`Source`** 버튼 다시 클릭 → 시각적 확인
7. Job Title, Location, Company Name 입력 후 **Submit**

> 에러 발생 시: 우측 `</> 소스 편집` 탭에서 직접 수정 → `✓ 적용` 버튼

