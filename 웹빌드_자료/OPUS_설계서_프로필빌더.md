# BRIDGE 프로필 메일 빌더 — Opus 최종 설계서 v2
> 작성: 2026-03-18 | 02.JPG + 03.JPG 실사례 역공학 완료 + 보안점검 반영
> Sonnet 분석 → Opus 구현

---

## ⚠️ 보안 재점검 결과 — Opus 구현 전 필수 반영 (2026-03-18)

| 항목 | 판정 | 조치 |
|------|------|------|
| SQL f-string 패턴 7개 | ✅ PASS | 전체 화이트리스트 검증 확인 |
| HMAC_SECRET 폴백 | ⚠️ WARNING | ADMIN_API_KEY로 폴백 — 실제 무력화 아님, .env 명시 권장 |
| CSP unsafe-inline | ⚠️ WARNING | API서버는 HTML 미렌더링 — 실질 위험 없음 |
| IDOR / 인증 우회 | ✅ PASS | 모든 관리자 엔드포인트 _check_admin() 선행 확인 |
| 암호화 구현 | ✅ PASS | Fail-Closed, gitignore 확인 |
| 로그 이메일 평문 기록 | ⚠️ WARNING | _smtp_send() 로그 + profile_sends.to_email 평문 저장 |
| **신규 API XSS** | 🔴 **필수** | html.escape() 미적용 — **Opus 구현 시 반드시 적용** |
| **암호화 필드 LIKE 검색** | 🔴 **필수** | full_name 암호화 저장 → LIKE 불가 → 평문 필드만 검색 |

### DB 컬럼명 불일치 (실측 확인)
| 설계서 필드 | DB 실제 컬럼 | 상태 |
|-------------|-------------|------|
| `sheet_number` | 없음 | ⚠️ ALTER TABLE 필요 (설계서 반영됨) |
| `korea_experience` | 없음 | 🔴 fallback 필요 → `experience` 사용 |
| `marital` | `married` | 🔴 컬럼명 수정 필요 |
| `personal` | `personal_consideration` | 🔴 컬럼명 수정 필요 |

---

## 0. 실사례 역공학 결과 (이미지 2장 비교 확정)

### 02.JPG 확인 사항
```
■5567영국 해외거주🏠
■5213캐나다 국내거주😊
■5569남아공 해외거주🏠
```

### 03.JPG 확인 사항
```
■5271영국 국내거주😊
■5683남아공 국내거주😊
■5579미국 국내거주😊
```

### ✅ 최종 확정 헤더 포맷
```
■{번호}{국적} {거주구분}거주{거주이모지}
```
- **국기 이모지 없음** (이전 설계서의 FLAG_MAP 불필요 → 제거)
- 국내거주 = 😊, 해외거주 = 🏠
- 국내/해외 판별: `current_location`에 "Korea/한국/서울/부산..." 포함 여부

---

## 1. 프로필 카드 HTML 최종 스펙 (실사례 기준)

```
■{번호}{국적} {거주구분}거주{거주이모지}
[사진: 60×60px 원형, 왼쪽 float]

•선호지역 자격 기타: {area_prefs} | {cert}
•경력 주거 희망급여: {경력라벨} | {housing} | {salary}
•리크루터 인터뷰: {recruiter_memo}
•레퍼런스: {reference}
🟡희망사항: {preferences}    ← background:#FFFF00 span
🟡기피사항: {dislikes}        ← background:#FFFF00 span
•타겟 근로개시: {target} | {start}
```

### 경력 라벨 로직 (03.JPG 실사례 "원 한국 1년차" 확인)
```python
# "원" = 원래 외국 출신 (모든 강사 공통)
# "한국 N년차" = korea_experience 필드
if korea_experience:
    exp_label = f"원 한국 {korea_experience}년차"
elif experience:
    exp_label = f"{experience}년"
else:
    exp_label = "—"
```

### 자격(cert) 로직 (실사례 "테블 O" 확인)
```python
# 03.JPG: "서울경기 | 테블 O"
# "테블" = TEFL/TESOL/TESL 자격증 + 등급 O/A/B
# visa_type, arc_holders, education_level 순서로 fallback
cert = (c.get("arc_holders") or         # E-2, F-4 등
        c.get("visa_type") or
        c.get("education_level") or "—")
```

---

## 2. DB 필드 매핑 최종 확정 (실측 컬럼 기준)

| 표시 | DB 실제 컬럼 | Fallback | 비고 |
|------|------------|---------|------|
| 번호 | `sheet_number` | `id` (rowid) | ALTER TABLE 후 사용 |
| 국적 | `nationality` | — | 평문 |
| 거주구분 | `current_location` | "해외" | 평문 |
| 사진 | `photo_url` | `thumb_url` → 👤 | URL 검증 필수 |
| 선호지역 | `area_prefs` | — | 평문 |
| 자격 | `arc_holders` → `visa_type` → `education_level` | — | 평문 |
| 경력 | `experience` | — | 🔴 `korea_experience` 컬럼 없음 |
| 주거 | `housing_type` → `housing` → `housing_detail` | — | |
| 희망급여 | `desired_salary` → `placed_salary` | 협의 | |
| 리크루터 인터뷰 | `recruiter_memo` | — | 🔴 html.escape 필수 |
| 레퍼런스 | `reference` | — | 🔴 html.escape 필수 |
| 희망사항 | `preferences` | — | 🔴 html.escape 필수 |
| 기피사항 | `dislikes` | — | 🔴 html.escape 필수 |
| 타겟 | `target` → `target_level` | — | |
| 근로개시 | `start_month` → `start_date` | — | |

---

## 3. 이메일 전체 HTML 구조

```html
<!-- 인트로 -->
<p style="font-size:13px;color:#444;margin-bottom:20px">
안녕하세요. BRIDGE 원어민 강사 프로필을 공유드립니다.<br/>
Start date and preferences noted. Reference provided for review only.
</p>

<!-- 프로필 카드 × N (반복) -->
{profile_cards}

<!-- 푸터 고정 -->
<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
<p style="font-size:12px;color:#555;line-height:1.8">
BRIDGE는 강사의 인성을 가장 중요하게 여기며, 공정하고 차별 없는 채용을 지향합니다.<br/>
인터뷰는 Google Meet으로 진행됩니다.
</p>
<p style="font-size:12px;color:#555">
QR코드 스캔하여 BRIDGE와 채팅하기<br/>
<img src="{qr_url}" width="60" height="60" alt="QR"/>
</p>
<p style="font-size:11px;color:#555">Kind Regards,</p>
<p style="font-size:11px;color:#666;line-height:1.7">
■ 직업안정법 제34조 안내: 무자격자가 소개 비용을 청구하는 경우 신고 시 포상금 지급<br/>
(기업 및 법적 고지)
</p>
<p style="font-size:10px;color:#999;line-height:1.6">
본 메일은 지정된 수신자에게만 전달된 것으로 ... (기존 법적 고지 유지)
</p>
```

---

## 4. DB 변경사항

### `sheet_number` 컬럼 추가
```python
# api_server.py init_db() 내부에 추가
# try/except로 이미 있는 경우 무시
try:
    conn.execute("ALTER TABLE candidates ADD COLUMN sheet_number INTEGER DEFAULT NULL")
    conn.commit()
except sqlite3.OperationalError:
    pass  # 이미 존재
```

---

## 5. 새 API 엔드포인트 2개

### 5-1. `POST /api/admin/candidates/build-profile-html`
```python
class BuildProfileHtmlBody(BaseModel):
    candidate_ids: list[str]       # candidate_id 목록 (순서 = 카드 순서)
    include_intro: bool = True
    include_footer: bool = True

@app.post("/api/admin/candidates/build-profile-html", tags=["admin"])
async def build_profile_html(request: Request, body: BuildProfileHtmlBody):
    _check_admin(request)
    # 각 candidate_id로 DB 조회 → _build_profile_card_v2() 호출
    # 전체 이메일 HTML 조합 후 반환
    return ok(data={"html": full_html, "count": len(body.candidate_ids)})
```

### 5-2. `GET /api/admin/candidates/profile-search`
```python
# ?q=검색어&limit=20
# 관리자 전용 경량 검색 (프로필 빌더 UI용)
# 반환: candidate_id, sheet_number, nationality, current_location, photo_url, status
@app.get("/api/admin/candidates/profile-search", tags=["admin"])
async def profile_search(request: Request, q: str = "", limit: int = 20):
    _check_admin(request)
    # 🔴 중요: full_name은 AES-256-GCM 암호화 저장 → LIKE 검색 불가 (항상 0건)
    # 반드시 평문 저장 필드만 검색 대상으로 사용:
    #   nationality, area_prefs, current_location, status (평문 OK)
    #   full_name, email, mobile_phone, kakaotalk (암호화 → LIKE 불가)
    # WHERE nationality LIKE ? OR area_prefs LIKE ? OR current_location LIKE ?
    # status='Active' 우선 정렬 (ORDER BY CASE WHEN status='Active' THEN 0 ELSE 1 END)
```

---

## 6. `_build_profile_card_v2()` 최종 Python 코드 (보안 재점검 반영)

```python
import html as _html  # 파일 상단에 추가

def _build_profile_card_v2(c: dict) -> str:
    """실사례(02.JPG, 03.JPG) 기준 프로필 카드. 기존 _build_profile_card() 건드리지 않음."""

    # 번호
    num = c.get("sheet_number") or c.get("id", "")

    # 국적 + 거주구분
    # 🔴 보안: nationality None 안전 처리
    nat = (c.get("nationality") or "").strip()
    loc = (c.get("current_location") or "").lower()
    is_korea = any(k in loc for k in ["korea", "한국", "서울", "부산", "대구", "인천",
                                       "수원", "경기", "광주", "대전", "울산"])
    residence = "국내" if is_korea else "해외"
    res_emoji = "😊" if is_korea else "🏠"

    # 사진 — URL은 XSS 위험 없이 안전하게 처리 (http/https만 허용)
    raw_photo = c.get("photo_url") or c.get("thumb_url") or ""
    photo_url = raw_photo if raw_photo.startswith(("http://", "https://")) else ""
    if photo_url:
        photo_html = (
            f'<img src="{_html.escape(photo_url)}" width="65" height="65" alt="" '
            f'style="border-radius:50%;object-fit:cover;object-position:top;'
            f'float:left;margin:0 12px 8px 0;display:block"/>'
        )
    else:
        photo_html = (
            '<div style="width:65px;height:65px;border-radius:50%;background:#e5e7eb;'
            'float:left;margin:0 12px 8px 0;font-size:28px;line-height:65px;'
            'text-align:center">👤</div>'
        )

    # 자격
    cert = (c.get("arc_holders") or c.get("visa_type") or c.get("education_level") or "")

    # 선호지역 + 자격
    area = c.get("area_prefs") or "—"
    cert_str = f"{area} | {cert}" if cert else area

    # 경력
    # 🔴 DB에 korea_experience 컬럼 없음 → experience로 fallback
    kor_exp = str(c.get("korea_experience") or "").strip()   # ALTER TABLE 후 채워질 값
    exp     = str(c.get("experience") or "").strip()
    if kor_exp:
        exp_label = f"원 한국 {kor_exp}년차"
    elif exp:
        exp_label = f"원 한국 {exp}년차"   # experience를 korea_experience로 표시
    else:
        exp_label = "—"

    # 주거
    housing = (c.get("housing_type") or c.get("housing") or c.get("housing_detail") or "—")

    # 급여
    salary = c.get("desired_salary") or c.get("placed_salary") or "협의"

    # 🔴 보안 필수: DB 필드 → html.escape() 적용 (XSS 방어)
    interview = _html.escape(c.get("recruiter_memo") or "—")
    reference = _html.escape(c.get("reference") or "—")
    prefs     = _html.escape(c.get("preferences") or "—")
    dislik    = _html.escape(c.get("dislikes") or "—")

    # 타겟 + 근로개시
    target = c.get("target") or c.get("target_level") or ""
    start  = c.get("start_month") or c.get("start_date") or ""
    target_str = " | ".join(filter(None, [target, f"{start}시작" if start else ""])) or "—"

    YEL = "background:#FFFF00;font-weight:bold;padding:1px 3px"

    return f"""<div style="margin:20px 0 4px">
  <strong style="font-size:14px">■{num}{nat} {residence}거주{res_emoji}</strong>
</div>
<div style="margin-bottom:4px;overflow:hidden">
  {photo_html}
  <div style="font-size:13px;line-height:2.0;color:#222">
    •선호지역 자격 기타: {_html.escape(cert_str)}<br>
    •경력 주거 희망급여: {exp_label} | {_html.escape(housing)} | {_html.escape(salary)}<br>
    •리크루터 인터뷰: {interview}<br>
    •레퍼런스: {reference}<br>
    <span style="{YEL}">희망사항</span>: {prefs}<br>
    <span style="{YEL}">기피사항</span>: {dislik}<br>
    •타겟 근로개시: {_html.escape(target_str)}
  </div>
  <div style="clear:both"></div>
</div>
<hr style="border:none;border-top:1px dashed #d1d5db;margin:12px 0"/>
"""
```

---

## 7. 프론트엔드 최종 설계 (mail-send/page.tsx)

### 탭 구조 (기존 코드 최소 변경)
```typescript
// 추가할 state 딱 2개
const [activeTab, setActiveTab] = useState<'mail' | 'builder'>('mail')

// 탭 버튼 (헤더 h1 아래에 추가)
<div className="flex gap-1 border-b border-[#e5e5e7] mb-4">
  <button onClick={() => setActiveTab('mail')}
    className={activeTab==='mail' ? '탭활성스타일' : '탭비활성스타일'}>
    ✉️ 메일 발송
  </button>
  <button onClick={() => setActiveTab('builder')}
    className={activeTab==='builder' ? '탭활성스타일' : '탭비활성스타일'}>
    📋 프로필 빌더
  </button>
</div>

{activeTab === 'mail' && <기존JSX />}
{activeTab === 'builder' && <ProfileBuilder
  onInsert={(html) => {
    setBodyHtml(html)
    setSubject('📢BRIDGE 원어민 강사 소식 ! 국내/해외 프로필 확인하세요')
    setActiveTab('mail')
  }}
/>}
```

### ProfileBuilder 컴포넌트 (같은 파일 하단에 추가)
```typescript
function ProfileBuilder({ onInsert }: { onInsert: (html: string) => void }) {
  const { adminKey, signedFetch } = useAdminAuth()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState([])   // 순서 유지 배열
  const [previewHtml, setPreviewHtml] = useState('')
  const [loading, setLoading] = useState(false)

  // 300ms debounce 검색
  // 선택 추가/제거
  // "HTML 생성" → POST /api/admin/candidates/build-profile-html
  // "본문에 삽입" → onInsert(previewHtml)
}
```

---

## 8. 보안 점검 결과 반영

Opus 구현 시 아래 3가지 추가 적용:

### 8-1. ✅ 이미 PASS (건드리지 말 것)
- PII 마스킹: 프로필 카드에 이름/이메일/전화번호 포함 금지 (유지)
- Rate limit: 기존 설정 유지
- 파일 업로드 검증: 기존 유지

### 8-2. ⚠️ WARNING → 설계 반영
**SQL f-string 컬럼명 패턴**: 신규 엔드포인트에서 컬럼명은 **반드시 화이트리스트 검증 후** f-string 사용
```python
# 신규 API에서 사용할 화이트리스트
_PROFILE_SAFE_COLS = frozenset({
    "candidate_id", "sheet_number", "nationality", "current_location",
    "photo_url", "thumb_url", "area_prefs", "visa_type", "arc_holders",
    "experience", "korea_experience", "housing_type", "housing",
    "housing_detail", "desired_salary", "placed_salary", "recruiter_memo",
    "reference", "preferences", "dislikes", "target", "target_level",
    "start_month", "start_date", "education_level", "status", "id",
})
```

**HMAC_SECRET**: Opus는 Render 환경변수 확인 방법 주석으로 안내만 (직접 설정은 관리자 수동)
```python
# ⚠️ 주의: HMAC_SECRET 환경변수가 Render에 설정되어야 HMAC 재전송 공격 방어 활성화
# Render Dashboard → bridge-n7hk → Environment → HMAC_SECRET 확인
```

**CSP unsafe-inline**: 현재 유지 (Nonce 방식 전환은 별도 작업으로 분리)

---

## 9. Opus 실행 순서 (확정)

```
Step 0: DB 마이그레이션 (5분)
  └─ api_server.py init_db() 에 sheet_number 컬럼 추가

Step 1: Python 함수 + API 추가 (30분)
  ├─ _build_profile_card_v2() 함수 추가 (기존 건드리지 말 것)
  ├─ POST /api/admin/candidates/build-profile-html
  └─ GET  /api/admin/candidates/profile-search

Step 2: 프론트엔드 탭 + ProfileBuilder (40분)
  ├─ activeTab state 추가
  ├─ 탭 버튼 UI (h1 아래)
  ├─ 기존 JSX를 activeTab==='mail' 조건부로 감싸기
  └─ ProfileBuilder 컴포넌트 구현 (같은 파일 하단)

Step 3: 검증 (15분)
  ├─ python -m py_compile api_server.py → OK 확인
  ├─ cd web_frontend && npm run build → 에러 없음 확인
  └─ git add -A && git commit -m "feat: 프로필 메일 빌더" && git push

총 예상: 90분 (2x 시간대 내 충분히 완료 가능)
```

---

## 10. 완료 체크리스트

- [ ] `/admin/mail-send` → "프로필 빌더" 탭 보임
- [ ] 이름/국적 검색 → 후보자 목록 출력
- [ ] 후보자 선택 → 선택 목록에 추가
- [ ] "HTML 생성" → 03.JPG 스타일 카드 생성 확인
  - [ ] 헤더 형식: `■{번호}{국적} {거주구분}거주{이모지}`
  - [ ] 사진 원형 float:left
  - [ ] 노란배경 희망사항/기피사항
- [ ] "본문에 삽입" → 탭 1 전환 + 제목·본문 자동입력
- [ ] `python -m py_compile api_server.py` → PASS
- [ ] `npm run build` → PASS
- [ ] git push → `main -> main` 확인

---

## 참고 파일
- 실사례 이미지: `웹빌드_자료/02.JPG`, `03.JPG`
- Apps Script: `웹빌드_자료/apps_script_skeleton.js` (완성본)
- 기존 메일 발송 UI: `web_frontend/src/app/admin/mail-send/page.tsx`
- 기존 프로필 카드 함수: `api_server.py:2244` (`_build_profile_card`)

---
*v2 최종확정: 2026-03-18 | 실사례 2장 역공학 + 보안점검 반영 완료*
