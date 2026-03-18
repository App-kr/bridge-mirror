# BRIDGE 프로필 메일 빌더 — Opus 구현 명령서
> 작성: 2026-03-18 | Sonnet 설계 → Opus 구현
> 작업 시간: 2x 타임 내 (약 90분 예상)
> v1.2: apps_script v3 완전 검증 완료 (xlsx 원본 파싱 기준)

## ✅ 사전 완료 사항 (Opus 작업 불필요)

| 항목 | 파일 | 상태 |
|------|------|------|
| 구글시트 Apps Script | `웹빌드_자료/apps_script_skeleton.js` v3 | ✅ 완성 — 구글시트에 붙여넣기만 하면 됨 |
| 컬럼 매핑 검증 | xlsx sharedStrings 직접 파싱 (2026-03-18) | ✅ Form 40열 / New 50열 모두 확인 |
| 발견된 오류 수정 | Form 시트 탭명=`Form` (Source 아님) | ✅ v3에 반영 |
| | Form col 15 = ARC holders (Passport 아님) | ✅ v3에 반영 |
| | New AM(39) = Passport 누락 → 추가 | ✅ v3에 반영 |
| | 배열 크기 49→50, 폼 읽기 38→40 | ✅ v3에 반영 |

---

## ⚡ 세션 시작 즉시 실행 (Step 0)

```bash
# 1. DB 수호자 체크 — 건수 이탈 시 즉시 중단
python -c "
import sqlite3, os
conn = sqlite3.connect('Q:/Claudework/bridge base/master.db')
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
ic = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM candidates')
c = cur.fetchone()[0]
conn.close()
print(f'integrity={ic} | candidates={c}')
assert ic == 'ok', '🚨 DB 손상!'
assert c >= 3000, f'🚨 candidates 이상: {c}'
print('✅ DB OK')
"

# 2. 실제 DB 컬럼 확인 (설계서와 대조)
python -c "
import sqlite3
conn = sqlite3.connect('Q:/Claudework/bridge base/master.db')
cur = conn.cursor()
cur.execute('PRAGMA table_info(candidates)')
cols = [row[1] for row in cur.fetchall()]
conn.close()
print('PK 후보:', [c for c in cols if 'id' in c.lower()])
print('경력 관련:', [c for c in cols if 'exp' in c.lower() or 'employ' in c.lower()])
print('주거 관련:', [c for c in cols if 'hous' in c.lower()])
print('결혼 관련:', [c for c in cols if 'marr' in c.lower() or 'marit' in c.lower()])
print('개인 관련:', [c for c in cols if 'personal' in c.lower()])
print('sheet 관련:', [c for c in cols if 'sheet' in c.lower() or 'number' in c.lower()])
"

# 3. 백업
python "Q:\Claudework\bridge base\tools\bridge_backup.py" backup "프로필빌더구현" --type pre-task
```

---

## 🎯 구현 목표

`admin/mail-send` 페이지에 **"프로필 빌더" 탭**을 추가한다.
- 관리자가 후보자를 검색 → 선택 → HTML 이메일 자동 생성 → 기존 메일 발송 탭으로 삽입
- 실사례 이미지(`02.JPG`, `03.JPG`) 기반 카드 포맷 구현

**설계 전문**: `웹빌드_자료/OPUS_설계서_프로필빌더.md` — 반드시 전체 읽고 시작

---

## 📋 구현 순서 (엄수)

### Step 1: DB 마이그레이션 (5분)

`api_server.py` 의 `init_db()` 함수에 아래 추가:

```python
# sheet_number 컬럼 추가 (이미 있으면 무시)
try:
    conn.execute("ALTER TABLE candidates ADD COLUMN sheet_number INTEGER DEFAULT NULL")
    conn.commit()
except sqlite3.OperationalError:
    pass  # 이미 존재
```

**Self-check**: `PRAGMA table_info(candidates)` 실행 → `sheet_number` 컬럼 확인

---

### Step 2: 파이썬 함수 추가 (30분)

**파일**: `api_server.py`

#### 2-1. 파일 상단 import 확인 (현재 없음 — 반드시 추가)
```python
import html as _html  # ← api_server.py 최상단 import 블록에 추가 필수
                      # 현재 api_server.py에 없음 (2026-03-18 실측 확인)
```

#### 2-2. `_build_profile_card_v2()` 함수 추가
- 기존 `_build_profile_card()` (line ~2244) **절대 수정 금지** — 그 아래에 새 함수 추가
- 설계서 섹션 6의 완성 코드 그대로 사용

**필수 보안 체크리스트**:
- [ ] `html.escape()` 적용: `recruiter_memo`, `reference`, `preferences`, `dislikes`
- [ ] `html.escape()` 적용: `cert_str`, `housing`, `salary`, `target_str`, `photo_url`
- [ ] `photo_url`은 `http://` 또는 `https://`로 시작하는 경우만 허용
- [ ] DB에 `korea_experience` 컬럼 없음 → Step 0 확인 결과 기준으로 분기

**DB 컬럼 불일치 처리** (Step 0 실측 결과 반영):
```python
# korea_experience가 없으면 experience로 fallback
kor_exp = str(c.get("korea_experience") or "").strip()
exp     = str(c.get("experience") or "").strip()
# married vs marital — 실측 결과 기준
housing = c.get("housing_type") or c.get("housing") or c.get("housing_detail") or "—"
```

#### 2-3. `GET /api/admin/candidates/profile-search` 추가
```python
@app.get("/api/admin/candidates/profile-search", tags=["admin"])
async def profile_search(request: Request, q: str = "", limit: int = 20):
    _check_admin(request)
```
- **반드시 평문 필드만 LIKE 검색**: `nationality`, `area_prefs`, `current_location`
- **암호화 필드 LIKE 절대 금지**: `full_name`, `email`, `mobile_phone`, `kakaotalk`
- 반환 필드: `candidate_id`(또는 실측 PK명), `sheet_number`, `nationality`, `current_location`, `photo_url`, `thumb_url`, `status`
- `STATUS='Active'` 우선 정렬: `ORDER BY CASE WHEN status='Active' THEN 0 ELSE 1 END, id DESC`
- WHERE 절 반드시 파라미터화: `WHERE nationality LIKE ? OR area_prefs LIKE ? OR current_location LIKE ?`
- 검색어 없을 때: 최근 20건 반환 (빈 결과 아님)

#### 2-4. `POST /api/admin/candidates/build-profile-html` 추가
```python
class BuildProfileHtmlBody(BaseModel):
    candidate_ids: list[str]
    include_intro: bool = True
    include_footer: bool = True
```
- 각 `candidate_id`로 DB 조회 → `_build_profile_card_v2()` 호출 → 전체 HTML 조합
- 인트로 + 카드들 + 푸터 = 완성 이메일 HTML
- 설계서 섹션 3 참고 (인트로/푸터 텍스트)

**Self-check Step 2**:
```bash
python -m py_compile api_server.py && echo "✅ COMPILE_OK"
# 에러 시 즉시 수정 (push 금지)
```

---

### Step 3: 프론트엔드 탭 추가 (40분)

**파일**: `web_frontend/src/app/admin/mail-send/page.tsx` (614줄, 2026-03-18 실측)

#### 3-1. state 1개 추가 (기존 state 근처에)
```typescript
const [activeTab, setActiveTab] = useState<'mail' | 'builder'>('mail')
```

#### 3-2. 탭 버튼 UI 추가 (기존 h1 태그 아래)
```tsx
<div className="flex gap-1 border-b border-[#e5e5e7] mb-4">
  <button
    onClick={() => setActiveTab('mail')}
    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      activeTab === 'mail'
        ? 'border-[#0071e3] text-[#0071e3]'
        : 'border-transparent text-[#6e6e73] hover:text-[#1d1d1f]'
    }`}
  >
    ✉️ 메일 발송
  </button>
  <button
    onClick={() => setActiveTab('builder')}
    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      activeTab === 'builder'
        ? 'border-[#0071e3] text-[#0071e3]'
        : 'border-transparent text-[#6e6e73] hover:text-[#1d1d1f]'
    }`}
  >
    📋 프로필 빌더
  </button>
</div>
```

#### 3-3. 기존 JSX를 조건부로 감싸기
기존 메일 발송 UI 전체를 `{activeTab === 'mail' && (...)}` 로 감싸기.

#### 3-4. 프로필 빌더 탭 추가
```tsx
{activeTab === 'builder' && (
  <ProfileBuilder
    onInsert={(html) => {
      setBodyHtml(html)
      setSubject('📢BRIDGE 원어민 강사 소식 ! 국내/해외 프로필 확인하세요')
      setActiveTab('mail')
    }}
  />
)}
```

#### 3-5. ProfileBuilder 컴포넌트 구현 (파일 하단, export 전에 추가)

```typescript
function ProfileBuilder({ onInsert }: { onInsert: (html: string) => void }) {
  const { adminKey, signedFetch } = useAdminAuth()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [selected, setSelected] = useState<any[]>([])  // 순서 유지
  const [previewHtml, setPreviewHtml] = useState('')
  const [loading, setLoading] = useState(false)

  // 검색 (300ms debounce)
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!adminKey) return
      const res = await signedFetch(
        `/api/admin/candidates/profile-search?q=${encodeURIComponent(query)}&limit=20`
      )
      const data = await res.json()
      setResults(data.data || [])
    }, 300)
    return () => clearTimeout(timer)
  }, [query, adminKey])

  // 선택 추가 (중복 방지)
  const addCandidate = (c: any) => {
    if (!selected.find(s => s.candidate_id === c.candidate_id)) {
      setSelected(prev => [...prev, c])
    }
  }

  // 순서 변경 (위/아래)
  const moveUp = (idx: number) => {
    if (idx === 0) return
    setSelected(prev => {
      const arr = [...prev]
      ;[arr[idx-1], arr[idx]] = [arr[idx], arr[idx-1]]
      return arr
    })
  }

  const moveDown = (idx: number) => {
    setSelected(prev => {
      if (idx >= prev.length - 1) return prev
      const arr = [...prev]
      ;[arr[idx], arr[idx+1]] = [arr[idx+1], arr[idx]]
      return arr
    })
  }

  // HTML 생성
  const buildHtml = async () => {
    if (selected.length === 0) return
    setLoading(true)
    try {
      const res = await signedFetch('/api/admin/candidates/build-profile-html', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_ids: selected.map(c => c.candidate_id),
          include_intro: true,
          include_footer: true,
        }),
      })
      const data = await res.json()
      setPreviewHtml(data.data?.html || '')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-160px)]">
      {/* 왼쪽: 검색 + 결과 */}
      <div className="w-72 flex flex-col gap-3 shrink-0">
        <input
          type="text"
          placeholder="국적/지역 검색..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="w-full px-3 py-2 border border-[#d2d2d7] rounded-lg text-sm"
        />
        <div className="flex-1 overflow-y-auto border border-[#d2d2d7] rounded-lg divide-y divide-[#f0f0f0]">
          {results.map(c => (
            <button
              key={c.candidate_id}
              onClick={() => addCandidate(c)}
              className="w-full px-3 py-2 text-left text-sm hover:bg-[#f5f5f7] flex items-center gap-2"
            >
              {c.photo_url || c.thumb_url ? (
                <img src={c.photo_url || c.thumb_url} className="w-8 h-8 rounded-full object-cover object-top shrink-0" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-[#e5e7eb] flex items-center justify-center text-xs shrink-0">👤</div>
              )}
              <div>
                <div className="font-medium">{c.sheet_number || c.candidate_id}</div>
                <div className="text-[#6e6e73] text-xs">{c.nationality} · {c.current_location}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 가운데: 선택 목록 */}
      <div className="w-56 flex flex-col gap-2 shrink-0">
        <div className="text-xs font-medium text-[#6e6e73]">선택된 후보자 ({selected.length})</div>
        <div className="flex-1 overflow-y-auto border border-[#d2d2d7] rounded-lg divide-y divide-[#f0f0f0]">
          {selected.map((c, idx) => (
            <div key={c.candidate_id} className="px-3 py-2 flex items-center gap-1 text-sm">
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{c.sheet_number || c.candidate_id}</div>
                <div className="text-[#6e6e73] text-xs truncate">{c.nationality}</div>
              </div>
              <div className="flex flex-col gap-0.5">
                <button onClick={() => moveUp(idx)} className="text-[#6e6e73] hover:text-[#1d1d1f] leading-none">▲</button>
                <button onClick={() => moveDown(idx)} className="text-[#6e6e73] hover:text-[#1d1d1f] leading-none">▼</button>
              </div>
              <button onClick={() => setSelected(prev => prev.filter((_, i) => i !== idx))}
                className="text-[#ff3b30] hover:text-red-700 text-xs ml-1">✕</button>
            </div>
          ))}
        </div>
        <button
          onClick={buildHtml}
          disabled={selected.length === 0 || loading}
          className="w-full py-2 bg-[#0071e3] text-white text-sm font-medium rounded-lg disabled:opacity-40 hover:bg-[#0077ed]"
        >
          {loading ? '생성 중...' : 'HTML 생성'}
        </button>
      </div>

      {/* 오른쪽: 미리보기 */}
      <div className="flex-1 flex flex-col gap-2 min-w-0">
        <div className="text-xs font-medium text-[#6e6e73]">HTML 미리보기</div>
        <div className="flex-1 border border-[#d2d2d7] rounded-lg overflow-auto bg-white p-4">
          {previewHtml ? (
            <div dangerouslySetInnerHTML={{ __html: previewHtml }} />
          ) : (
            <div className="text-[#6e6e73] text-sm text-center mt-8">
              후보자를 선택 후 "HTML 생성" 클릭
            </div>
          )}
        </div>
        <button
          onClick={() => previewHtml && onInsert(previewHtml)}
          disabled={!previewHtml}
          className="py-2 bg-[#34c759] text-white text-sm font-medium rounded-lg disabled:opacity-40 hover:bg-[#2db34a]"
        >
          ✅ 본문에 삽입 (메일 발송 탭으로 이동)
        </button>
      </div>
    </div>
  )
}
```

**Self-check Step 3**:
```bash
cd "Q:\Claudework\bridge base\web_frontend"
npm run build 2>&1 | tail -20
# 에러 시 즉시 수정
```

---

### Step 4: 최종 검증 + Push (15분)

```bash
# 1. Python 컴파일
cd "Q:\Claudework\bridge base"
python -m py_compile api_server.py && echo "✅ COMPILE_OK"

# 2. 프론트엔드 빌드
cd web_frontend && npm run build && echo "✅ BUILD_OK"

# 3. Lint
npm run lint 2>&1 | grep -E "error|Error" || echo "✅ LINT_OK"

# 4. Git
cd "Q:\Claudework\bridge base"
git add api_server.py web_frontend/src/app/admin/mail-send/page.tsx
git commit -m "feat: 프로필 메일 빌더 탭 추가 (build-profile-html, profile-search API)"
git push origin main
# "main -> main" 출력 필수 확인
```

---

## 🚫 절대 금지 사항

| 금지 | 이유 |
|------|------|
| 기존 `_build_profile_card()` 수정 | 기존 이메일 발송 기능 깨짐 |
| `full_name LIKE` 검색 | AES-256-GCM 암호화 → 항상 0건 |
| html.escape() 없이 DB 필드 → HTML 삽입 | XSS 취약점 |
| 비밀번호 변경/추가 | CLAUDE.md 절대 규칙 |
| 하드코딩 API 키/비밀번호 | 보안 위반 |
| HERO 섹션 수정 | LOCKED |
| 구현 중 중간보고 | CLAUDE.md 규칙 |
| 추측 기능 추가 | 최소 코드 원칙 |

---

## 🔴 에러 발생 시 자가 점검 프로토콜

에러가 나면 즉시:
1. **DB 컬럼 재확인** → `PRAGMA table_info(candidates)` — 컬럼명 정확하게
2. **타입 오류** → `Optional[str]` 처리 (None 값 안전 처리)
3. **import 누락** → `import html as _html` 파일 상단 확인
4. **TypeScript 에러** → `any[]` 타입 사용 허용 (완벽한 타입보다 동작 우선)
5. **API 404** → `@app.get` / `@app.post` 데코레이터 직전 빈 줄 없는지 확인
6. **빌드 에러** → `useEffect`, `useState` import 확인, `React` import 확인

---

## ✅ 완료 체크리스트 (전부 통과 전까지 Push 금지)

- [ ] `python -m py_compile api_server.py` → PASS
- [ ] `npm run build` → PASS (warning은 허용, error는 금지)
- [ ] `/admin/mail-send` → "프로필 빌더" 탭 버튼 보임
- [ ] 검색창에 국적 입력 → 후보자 목록 출력
- [ ] 후보자 클릭 → 선택 목록에 추가 (중복 방지)
- [ ] ▲▼ 버튼으로 순서 변경
- [ ] "HTML 생성" → 카드 HTML 생성 (`■{번호}{국적} {거주구분}거주{이모지}` 포맷)
- [ ] 사진 원형 `float:left` 확인
- [ ] 노란배경 희망사항/기피사항 확인
- [ ] "본문에 삽입" → 탭 1 전환 + 본문/제목 자동입력
- [ ] git push → `main -> main` 확인

---

## 📁 참조 파일 경로

```
Q:\Claudework\bridge base\
├── api_server.py                              ← 백엔드 (Step 1, 2)
├── web_frontend\src\app\admin\mail-send\page.tsx  ← 프론트 (Step 3)
├── master.db                                  ← DB (건드리지 말 것)
├── 웹빌드_자료\
│   ├── OPUS_설계서_프로필빌더.md              ← 상세 설계서 (필독)
│   ├── 02.JPG                                 ← 실사례 이미지 1
│   ├── 03.JPG                                 ← 실사례 이미지 2
│   └── apps_script_skeleton.js                ← 구글시트 스크립트 (이번 작업 대상 아님)
└── CLAUDE.md                                  ← 절대 규칙
```

---

## 📊 완료 보고 형식

```
✅ 프로필 메일 빌더 완료 — build-profile-html·profile-search API + ProfileBuilder UI 구현
📋 다음 추천: Render 배포 후 실제 카드 생성 QA
```

---

*OPUS_명령서.md v1.2 — 2026-03-18 | Sonnet 4.6 설계 완료 | apps_script v3 xlsx 실측 기준 완전 검증*
