# BRIDGE 프로필 메일 빌더 — Opus 설계서
> 작성: 2026-03-18 | Sonnet 분석 → Opus 구현
> 목표: 02.JPG 이메일 포맷 완벽 재현 + 관리자 UI 구축

---

## 1. 02.JPG 역공학 분석 (실제 이미지 기준)

### 이메일 전체 구조
```
제목: 📢BRIDGE 원어민 강사 소식 ! 국내/해외 프로필 확인하세요
발신: Bridge <bridgejobkr@naver.com>

[인트로 문구]
안녕하세요. BRIDGE 원어민 강사 프로필을 공유드립니다.
Start date and preferences noted. Reference provided for review only.

[프로필 카드 × N]

[서명 + 법적 고지]
```

### 프로필 카드 1개 포맷 (■5567영국 해외거주🏠)
```
■{번호}{국적} {거주구분}거주{거주이모지}
[사진: 원형 60~70px, 카드 왼쪽 상단]

•선호지역 자격 기타: {area_prefs} | {cert} | {기타}
•경력 주거 희망급여: {경력라벨} | {housing} | {desired_salary}
•리크루터 인터뷰: {recruiter_memo}
•레퍼런스: {reference}
🟡희망사항: {preferences}   ← 노란 배경 하이라이트
🟡기피사항: {dislikes}       ← 노란 배경 하이라이트
•타겟 근로개시: {target} | {start_date}~
```

### 세부 필드 매핑 (DB → 표시)

| 표시 항목 | DB 컬럼 | 가공 방식 |
|-----------|---------|----------|
| 번호 | `sheet_number` (없으면 `id`) | 그대로 |
| 국적 | `nationality` | 그대로 |
| 국기 이모지 | `nationality` | 아래 매핑표 |
| 거주구분 | `current_location` | "Korea/한국" 포함 → 국내, 아니면 해외 |
| 거주이모지 | 거주구분 결과 | 국내=😊, 해외=🏠 |
| 사진 | `photo_url` | 원형 img 태그 |
| 선호지역 | `area_prefs` | 그대로 |
| 자격/기타 | `visa_type` or `arc_holders` + `education_level` | 파이프로 연결 |
| 경력라벨 | `experience` + `korea_experience` | "원 한국 {N}년차" 또는 "{N}년" |
| 주거 | `housing_type` → `housing` 순서로 fallback | 그대로 |
| 희망급여 | `desired_salary` → `placed_salary` | 그대로 |
| 리크루터 인터뷰 | `recruiter_memo` | 그대로 |
| 레퍼런스 | `reference` | 그대로 |
| 희망사항 | `preferences` | 노란배경 `<span>` |
| 기피사항 | `dislikes` | 노란배경 `<span>` |
| 타겟 | `target` or `target_level` | 그대로 |
| 근로개시 | `start_month` → `start_date` | 그대로 |

### 국적 → 국기 이모지 매핑
```javascript
const FLAG_MAP = {
  '미국': '🇺🇸', 'American': '🇺🇸', 'USA': '🇺🇸',
  '캐나다': '🇨🇦', 'Canadian': '🇨🇦', 'Canada': '🇨🇦',
  '영국': '🇬🇧', 'British': '🇬🇧', 'UK': '🇬🇧',
  '남아공': '🇿🇦', 'South African': '🇿🇦', 'South Africa': '🇿🇦',
  '뉴질랜드': '🇳🇿', 'New Zealand': '🇳🇿', 'Kiwi': '🇳🇿',
  '호주': '🇦🇺', 'Australian': '🇦🇺', 'Australia': '🇦🇺',
  '아일랜드': '🇮🇪', 'Irish': '🇮🇪', 'Ireland': '🇮🇪',
  '필리핀': '🇵🇭', 'Filipino': '🇵🇭', 'Philippines': '🇵🇭',
}
// fallback: 국적 텍스트 그대로
```

---

## 2. DB 변경사항 (최소)

### `sheet_number` 컬럼 추가
기존 candidates 테이블에 컬럼 추가 (없으면 폼 번호 표시 불가):
```sql
ALTER TABLE candidates ADD COLUMN sheet_number INTEGER DEFAULT NULL;
```
- 기존 레코드: NULL (표시 시 DB `id` 로 fallback)
- 새 Apps Script 등록자: Google Sheet D열 번호로 채워질 예정
- **주의**: api_server.py `init_db()` 에 `IF NOT EXISTS` 형태로 추가할 것

---

## 3. 새 API 엔드포인트

### `GET /api/admin/candidates/profile-preview`
```python
# 쿼리: ?ids=cnd_xxx,cnd_yyy (candidate_id 목록)
# 반환: 각 후보자의 프로필 카드용 경량 데이터
# PII 포함 (관리자 전용, X-Admin-Key 필수)
# 반환 필드:
{
  "candidate_id": "cnd_xxx",
  "sheet_number": 5567,        # 없으면 DB id
  "nationality": "영국",
  "current_location": "UK",
  "photo_url": "https://...",
  "area_prefs": "서울경기남부",
  "visa_type": "E-2",
  "education_level": "MA",
  "experience": "3",
  "korea_experience": "1",
  "housing_type": "하우징 제공 최탈",
  "desired_salary": "280 이상",
  "recruiter_memo": "애들이 재밌게...",
  "reference": "업무는 미리...",
  "preferences": "프린타임이 구분된...",
  "dislikes": "의사소통이 안되며...",
  "target": "유치초등선호",
  "start_month": "4월",
}
```

### `POST /api/admin/candidates/build-profile-html`
```python
# body: { candidate_ids: ["cnd_xxx", "cnd_yyy"], include_intro: true }
# 반환: { html: "<완성된 이메일 HTML>" }
# 기능: 여러 후보자의 프로필 카드를 이어붙인 완성 HTML 반환
```

---

## 4. 프로필 카드 HTML 생성 함수 (Python)

### `_build_profile_card_v2(c: dict) -> str`
기존 `_build_profile_card()` 는 **건드리지 말 것** (호환성 유지).
새 함수를 별도로 추가:

```python
def _build_profile_card_v2(c: dict) -> str:
    """02.JPG 포맷 프로필 카드 HTML. 관리자 메일 빌더용."""

    # 번호
    num = c.get("sheet_number") or c.get("id", "")

    # 국적 + 국기
    nat = c.get("nationality", "")
    flag = _get_flag_emoji(nat)  # FLAG_MAP 참조

    # 거주구분
    loc = (c.get("current_location") or "").lower()
    is_korea = any(k in loc for k in ["korea", "한국", "서울", "부산", "대구", "인천"])
    residence = "국내" if is_korea else "해외"
    res_emoji = "😊" if is_korea else "🏠"

    # 사진
    photo_url = c.get("photo_url") or c.get("thumb_url") or ""
    photo_html = (
        f'<img src="{photo_url}" width="65" height="65" '
        f'style="border-radius:50%;object-fit:cover;float:left;margin:0 12px 8px 0" alt="" />'
    ) if photo_url else (
        '<div style="width:65px;height:65px;border-radius:50%;background:#e5e7eb;'
        'float:left;margin:0 12px 8px 0;display:flex;align-items:center;justify-content:center;'
        'font-size:24px">👤</div>'
    )

    # 경력 라벨: "원 한국 1년차" 또는 "{N}년"
    exp = c.get("experience") or c.get("teaching_experience") or ""
    kor_exp = c.get("korea_experience") or ""
    exp_label = f"원 한국 {kor_exp}년차" if kor_exp else (f"{exp}년" if exp else "—")

    # 자격/기타
    visa = c.get("visa_type") or c.get("arc_holders") or c.get("e_visa") or ""
    edu  = c.get("education_level") or ""
    cert_str = " | ".join(filter(None, [visa, edu])) or "—"

    # 주거
    housing = c.get("housing_type") or c.get("housing") or c.get("housing_detail") or "—"

    # 급여
    salary = c.get("desired_salary") or c.get("placed_salary") or "협의"

    # 인터뷰/레퍼런스
    interview = c.get("recruiter_memo") or "—"
    reference = c.get("reference") or "—"

    # 희망/기피 (노란 배경)
    prefs  = c.get("preferences") or ""
    dislik = c.get("dislikes") or ""

    # 타겟 + 근로개시
    target = c.get("target") or c.get("target_level") or ""
    start  = c.get("start_month") or c.get("start_date") or ""
    target_str = " | ".join(filter(None, [target, f"{start}시작~" if start else ""])) or "—"

    YELLOW = 'background:#FFFF00;font-weight:bold;padding:0 2px'

    return f"""
<div style="margin:16px 0 8px;clear:both">
  <strong style="font-size:14px">■{num}{flag} {nat} {residence}거주{res_emoji}</strong>
</div>
<div style="margin-bottom:16px;overflow:hidden">
  {photo_html}
  <div style="font-size:13px;line-height:1.9">
    <span>•선호지역 자격 기타: {c.get('area_prefs','—')} | {cert_str}</span><br/>
    <span>•경력 주거 희망급여: {exp_label} | {housing} | {salary}</span><br/>
    <span>•리크루터 인터뷰: {interview}</span><br/>
    <span>•레퍼런스: {reference}</span><br/>
    <span><span style="{YELLOW}">희망사항:</span> {prefs if prefs else '—'}</span><br/>
    <span><span style="{YELLOW}">기피사항:</span> {dislik if dislik else '—'}</span><br/>
    <span>•타겟 근로개시: {target_str}</span>
  </div>
  <div style="clear:both"></div>
</div>
<hr style="border:none;border-top:1px dashed #d1d5db;margin:4px 0 16px"/>
"""

def _get_flag_emoji(nationality: str) -> str:
    FLAG_MAP = {
        '미국':'🇺🇸','american':'🇺🇸','usa':'🇺🇸',
        '캐나다':'🇨🇦','canadian':'🇨🇦','canada':'🇨🇦',
        '영국':'🇬🇧','british':'🇬🇧','uk':'🇬🇧',
        '남아공':'🇿🇦','south african':'🇿🇦',
        '뉴질랜드':'🇳🇿','new zealand':'🇳🇿',
        '호주':'🇦🇺','australian':'🇦🇺','australia':'🇦🇺',
        '아일랜드':'🇮🇪','irish':'🇮🇪','ireland':'🇮🇪',
        '필리핀':'🇵🇭','filipino':'🇵🇭',
    }
    return FLAG_MAP.get(nationality.lower(), "")
```

---

## 5. 프론트엔드 설계 (mail-send/page.tsx)

### 탭 구조
기존 페이지에 탭을 **최상단**에 추가. 기존 코드는 Tab 1("메일 발송")로 이동, 신규 Tab 2("프로필 빌더") 추가.

```
[ 메일 발송 ]  [ 📋 프로필 빌더 ]   ← 탭 버튼
─────────────────────────────────────
Tab 1: 기존 메일 발송 UI (그대로 유지, 코드 변경 없음)
Tab 2: 프로필 빌더 (신규)
```

### Tab 2 레이아웃
```
┌─────────────────────────────────────────────────┐
│  📋 프로필 빌더                                   │
│  후보자를 검색·선택하여 이메일 HTML을 자동 생성합니다  │
├──────────────────────┬──────────────────────────┤
│ [검색 패널]           │ [선택된 후보자 목록]         │
│                      │                          │
│ 🔍 이름/번호 검색      │  ① 5567 영국 🇬🇧 해외  ×  │
│ ┌──────────────┐     │  ② 5213 캐나다 🇨🇦 국내 ×  │
│ │ 검색어 입력   │     │  ③ 5569 남아공 🇿🇦 해외 ×  │
│ └──────────────┘     │                          │
│                      │  ↑↓ 드래그로 순서 변경     │
│ [검색 결과 목록]       │                          │
│  ○ 5567 영국 해외 [+]│  [HTML 생성] [본문에 삽입]  │
│  ○ 5213 캐나다 국내[+]│                          │
│  ○ 5569 남아공 해외[+]│                          │
│  ...                 │                          │
├──────────────────────┴──────────────────────────┤
│ [미리보기]  ← 생성된 HTML을 이메일 스타일로 렌더링   │
│  ■5567영국 해외거주🏠                             │
│  [사진] •선호지역: 서울경기남부 ...                │
│  ■5213캐나다 국내거주😊                           │
│  [사진] •선호지역: 서울선호 ...                    │
└─────────────────────────────────────────────────┘
```

### 주요 State
```typescript
// Tab 2 전용 state
const [searchQuery, setSearchQuery] = useState('')
const [searchResults, setSearchResults] = useState<CandidateMini[]>([])
const [selectedCandidates, setSelectedCandidates] = useState<CandidateMini[]>([])
const [profileHtml, setProfileHtml] = useState('')
const [buildLoading, setBuildLoading] = useState(false)
const [profilePreview, setProfilePreview] = useState(false)

interface CandidateMini {
  candidate_id: string
  sheet_number: number | null
  nationality: string
  current_location: string
  display_label: string  // "5567 영국 해외거주"
}
```

### 주요 함수
```typescript
// 1. 검색 (300ms debounce)
const searchCandidates = async (q: string) => {
  const res = await signedFetch(`${API}/api/admin/candidates?search=${q}&limit=20`)
  const json = await res.json()
  setSearchResults(json.data?.candidates ?? [])
}

// 2. 후보자 추가/제거
const addCandidate = (c: CandidateMini) => {
  if (!selectedCandidates.find(s => s.candidate_id === c.candidate_id)) {
    setSelectedCandidates(prev => [...prev, c])
  }
}
const removeCandidate = (id: string) => {
  setSelectedCandidates(prev => prev.filter(c => c.candidate_id !== id))
}

// 3. HTML 생성 (API 호출)
const buildHtml = async () => {
  setBuildLoading(true)
  const ids = selectedCandidates.map(c => c.candidate_id)
  const res = await signedFetch(`${API}/api/admin/candidates/build-profile-html`, {
    method: 'POST',
    body: JSON.stringify({ candidate_ids: ids, include_intro: true }),
  })
  const json = await res.json()
  setProfileHtml(json.data?.html ?? '')
  setBuildLoading(false)
}

// 4. 본문에 삽입 → Tab 1으로 전환
const insertToMailBody = () => {
  setBodyHtml(profileHtml)  // Tab 1의 bodyHtml state 업데이트
  setSubject('📢BRIDGE 원어민 강사 소식 ! 국내/해외 프로필 확인하세요')
  setActiveTab('mail')      // Tab 1으로 전환
}
```

---

## 6. 구현 순서 (Opus 실행 순서)

### Step 0: DB 마이그레이션 (5분)
```python
# api_server.py init_db() 에 추가
conn.execute("""
  ALTER TABLE candidates ADD COLUMN sheet_number INTEGER DEFAULT NULL
""")
# 이미 있으면 에러 무시 처리 필요 (try/except sqlite3.OperationalError)
```

### Step 1: API 엔드포인트 추가 (20분)
파일: `api_server.py`

1. `_get_flag_emoji()` 헬퍼 함수 추가
2. `_build_profile_card_v2()` 함수 추가 (기존 `_build_profile_card` 건드리지 말 것)
3. `GET /api/admin/candidates/profile-preview` 엔드포인트
4. `POST /api/admin/candidates/build-profile-html` 엔드포인트
   - intro HTML + 카드들 + 기존 footer(법적고지) 조합
   - 완성 HTML 반환

### Step 2: 프론트엔드 탭 추가 (40분)
파일: `web_frontend/src/app/admin/mail-send/page.tsx`

1. 탭 state `activeTab: 'mail' | 'builder'` 추가
2. 탭 버튼 UI를 헤더 아래에 추가
3. 기존 JSX를 `activeTab === 'mail'` 조건부 렌더링으로 감싸기
4. `activeTab === 'builder'` 블록에 프로필 빌더 UI 구현

### Step 3: 검증 (15분)
```bash
# 백엔드 컴파일
python -m py_compile api_server.py && echo OK

# 프론트엔드 빌드
cd web_frontend && npm run build

# 수동 테스트
# 1. /admin/mail-send 접속 → "프로필 빌더" 탭 확인
# 2. 후보자 검색 → 선택 → HTML 생성 → 미리보기 확인
# 3. "본문에 삽입" → 메일 발송 탭으로 이동 + 본문 확인

# git push
cd .. && git add -A && git commit -m "feat: 프로필 메일 빌더 UI + API (02.JPG 포맷)" && git push
```

---

## 7. 절대 금지 사항 (CLAUDE.md)
- 기존 `_build_profile_card()` 함수 수정 금지 → 새 `_build_profile_card_v2()` 만 추가
- 기존 메일 발송 탭 UI 변경 금지 (탭 1 코드는 건드리지 말 것)
- 비밀번호 변경 금지
- SQL f-string 삽입 금지 → parameterized query만
- hard-delete 금지
- PII (이름, 이메일, 전화번호) → 프로필 카드 HTML에 포함 금지

---

## 8. 완료 기준
- [ ] `/admin/mail-send` 에서 "프로필 빌더" 탭 접근 가능
- [ ] 후보자 이름/번호 검색 → 선택 가능
- [ ] 1명 이상 선택 후 "HTML 생성" 클릭 → 02.JPG 스타일 카드 생성
- [ ] 미리보기에서 국기이모지·사진·노란하이라이트 확인
- [ ] "본문에 삽입" → 탭 1 본문 자동 입력 확인
- [ ] `npm run build` 통과
- [ ] `python -m py_compile api_server.py` 통과
- [ ] git push 완료

---
*설계 완료: 2026-03-18 | 구현: Opus*
