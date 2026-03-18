# ClaudeBlog 자동화 시스템 — 완전 기술 레퍼런스
> 최종 업데이트: 2026-03-18
> 환각 방지 전용 파일 — 코드 작성 전 반드시 확인

---

## 1. 프로젝트 경로 및 파일 구조

```
Q:/Claudework/ClaudeBlog/
├── main.py                        # 진입점 (--dry / --now / --draft / --publish-approved)
├── config.json                    # API키, 스케줄, 이미지 설정
├── inject_draft.py                # 승인 글 직접 Excel 삽입 스크립트
├── make_icon.py                   # 아이콘 생성 (Pillow)
├── 즉시발행.bat                    # 더블클릭 즉시 발행
├── .venv/Scripts/python.exe       # 전용 Python (절대 다른 python 쓰지 말 것)
├── modules/
│   ├── naver_uploader.py          # Selenium SE4 자동화 (핵심)
│   ├── content_generator.py       # Gemini/Claude 글 생성
│   ├── image_picker.py            # 이미지 선택
│   └── draft_manager.py          # Excel 초안 관리
├── rules/
│   ├── BLOG_RULES.md              # 핵심 글쓰기 규칙 v6.6
│   ├── PROMPT_V6.md               # 마스터 프롬프트 v6.6 (STEP 1~10)
│   ├── API_CONFIG.md              # API 설정 + 오류 대응
│   └── EDITOR_STEPS.md           # 에디터 8단계 + 인용구 탈출법
├── drafts/
│   └── draft_queue.xlsx           # 초안 대기열 (상태: 검토/승인/발행완료)
├── logs/
│   └── naver_cookies.json         # 네이버 쿠키 (만료 시 save_naver_session.py 재실행)
└── dry_outputs/                   # --dry 실행 결과 저장
```

---

## 2. Python 실행 명령 (절대경로 필수 / cd 없이)

```bash
# 테스트 (발행 없음)
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --dry

# 즉시 실행 (테스트용 — 실제 예약 발행)
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --now

# 초안 생성 → Excel 저장 (검토 상태)
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --draft

# 승인된 글만 발행
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --publish-approved
```

**금지:**
- `python`, `py` 단독 사용 금지
- `C:/Python314/python.exe` 사용 금지
- `cd Q:` 방식 금지 (bash에서 드라이브 전환 불가)

---

## 3. config.json 핵심 설정

```json
{
  "api": {
    "gemini_model": "gemini-2.0-flash-lite",       ← 키 이름 주의: gemini_model
    "anthropic_model": "claude-haiku-4-5-20251001",
    "temperature": 0.7,
    "gemini_api_keys": [
      {"name": "스칼렛",  "key": "AIzaSyDjh..."},
      {"name": "바이올렛", "key": "AIzaSyAY..."},
      {"name": "세번째",  "key": "AIzaSyBv..."},
      {"name": "네번째",  "key": "AIzaSyC-..."}
    ],
    "claude_fallback": true          ← 반드시 true 유지
  },
  "schedule": {
    "enabled": true,
    "publish_time": "09:30",
    "days_ahead": 2
  },
  "image_config": {
    "total_images_per_post": 7,
    "top_image_count": 1,
    "body_image_count": 6,
    "resize_width": 860,
    "image_quality": 88
  },
  "naver_id": "bridgejobkr",
  "blog_id": "bridgejob",
  "paths": {
    "base_dir": "Q:\\Claudework\\ClaudeBlog",
    "db_path": "logs/blog_history.db",
    "log_path": "logs/auto_post.log"
  }
}
```

**API 오류 대응:**
- Gemini 429 → 일일 한도 소진. 한국 시간 익일 오전 9시 초기화. Claude 폴백 자동 작동
- Claude 400 → Anthropic 크레딧 소진. console.anthropic.com/settings/plans 충전
- 쿠키 만료 → `save_naver_session.py` 실행

---

## 4. content_generator.py — 글 생성 구조

### 이미지 마커 위치 규칙
```
[서론 텍스트 2~3문장]
[IMG_TOP]                    ← 서론 직후 (본문 첫 줄 아님 — 중요)
[QUOTE]소제목1[/QUOTE]
[본문1단락]
[IMG_1]
[QUOTE]소제목2[/QUOTE]
[본문2단락]
[IMG_2]
...
[결론]
[내부 백링크 2개]
[에이전시 섹션]
[IMG_BANNER]
ⓒ 무단 전재 및 재배포 금지
중요 내용은 사실 확인 후 시행바랍니다
#원어민강사 #원어민채용 #원어민구인 [태그들] #서이추 #서이추환영
```

### [IMG_TOP] 강제 위치 조정 (L718~729)
```python
# body가 [IMG_TOP]으로 시작하면 → 서론 단락 이후로 이동
if body.startswith('[IMG_TOP]'):
    intro_para + '\n\n[IMG_TOP]\n\n' + remaining_body
```

### 1500자 미달 자동 확장 (_expand_body)
- API 호출 없이 4가지 확장 블록 중 1개 삽입
- 삽입 위치 우선순위: [IMG_2] > [IMG_1] > [IMG_TOP]

### 태그 구조 (L713)
```python
core[:13] + ["서이추", "서이추환영"]
# 1~3번 고정: 원어민강사, 원어민채용, 원어민구인
# 끝 2개 고정: 서이추, 서이추환영
# 총 11~13개
```

### 저작권 자동 삽입 (L749~756)
```python
# [IMG_BANNER] 직전에 자동 삽입
"ⓒ 무단 전재 및 재배포 금지\n중요 내용은 사실 확인 후 시행바랍니다"
# 주의: "중요 내용은" ← 공백 있음 (v6.6 수정사항)
```

---

## 5. naver_uploader.py — SE4 자동화 핵심 메서드

### 5-1. 제목 입력 (_set_title, L500~595)
```
1) ActionChains.move_to_element(sec).click()
   sec = .se-section-documentTitle
2) CE(contenteditable) 대기 루프 20×0.2s
3) ActionChains.move_to_element(inner).click()
   → Ctrl+A → pyperclip.copy(title) → Ctrl+V
Fallback1: JS execCommand('selectAll') + insertText
Fallback2: CE.focus() → Ctrl+A → Ctrl+V
마지막: 항상 _move_focus_to_body() 호출
```

### 5-2. 제목→본문 포커스 분리 (_move_focus_to_body, L684~698)
```javascript
// JS: .se-section-text div[contenteditable] 중 documentTitle 제외 → 첫 번째 CE click/focus
```

### 5-3. 제목 침범 방지 (_force_body_focus, L700~739)
```
조건: document.activeElement가 .se-section-documentTitle 내부인 경우
JS: 첫 번째 body CE 찾기 → Range.setStart(ce,0) → collapse(true) → removeAllRanges() → addRange(r)
Fallback: send_keys(Keys.TAB) × 2
```

### 5-4. 커버 이미지 (_set_cover_image, L597~636)
```
.se-section-documentTitle 내부 커버이미지 버튼 클릭
→ input[type='file'].send_keys(절대경로)
```

### 5-5. 인용구 삽입 (_insert_quote_block, L942~1001)
```
1) button[data-name='quotation'] 클릭 (SE4 툴바)
2) pyperclip.copy(one_line_text) → Ctrl+V (줄바꿈 제거한 1줄)
3) 탈출 시퀀스 (항상 실행):
   Keys.END → Keys.ENTER → Keys.BACKSPACE
4) 항상 _focus_after_quote() 호출 (_is_in_quote() 무관)
```

### 5-6. 인용구 탈출 (_focus_after_quote, L829~905) ★핵심
```javascript
// 메인 JS:
// 1) document.querySelectorAll('.se-section') 전체 순회
// 2) 마지막 quotation 클래스 섹션 index(qIdx) 찾기
// 3) qIdx 이후 섹션의 첫 번째 CE 찾기
// 4) ce.click() + ce.focus() + Range.setStart(ce,0) + collapse(true)

// Fallback1: ActionChains.move_to_element_with_offset(q_el, 0, height/2+60).click()
// Fallback2: send_keys(Keys.ESCAPE) → send_keys(Keys.ENTER)
```

**핵심 원칙**: `_is_in_quote()` 결과와 무관하게 항상 호출

### 5-7. 인용구 내부 여부 확인 (_is_in_quote, _ensure_outside_quote, L907~920)
```javascript
// _is_in_quote(): document.activeElement.closest('.se-section-quotation') !== null

// _ensure_outside_quote():
// if _is_in_quote(): Keys.ENTER + Keys.BACKSPACE → _focus_after_quote()
```

### 5-8. 본문 정렬 (_focus_body, L1140~1198)
```javascript
// .se-section-text div[contenteditable] (documentTitle 제외)
// Range.setStart(ce,0) → collapse(true)
// execCommand('justifyCenter')  ← 가운데 정렬
```

### 5-9. 텍스트 타이핑 (_type_text, L1200~1215)
```python
# 각 줄마다:
# 1) execCommand('justifyCenter')  (정렬 유지)
# 2) pyperclip.copy(line)
# 3) ActionChains Ctrl+V
# 4) Keys.ENTER
```

### 5-10. 본문+이미지 구조 (_write_body_with_images, L741~807)
```
마커 분할 처리:
  텍스트 세그먼트 → _type_text()
  [IMG_*] → 이미지 파일 삽입
  [QUOTE]...[/QUOTE] → _insert_quote_block()

전체 완료 후: JS Ctrl+A → execCommand('justifyCenter') (전체 가운데 정렬)
[IMG_BANNER] 없으면 → 자동 폴백 배너 삽입
```

### 5-11. 예약 발행 (_set_scheduled_time, L1337~1589)
```python
# 1) 예약 라디오 버튼: reserve_btn 클래스 제외 radio[type="radio"] click()
# 2) 시간 SELECT: hour_option / minute_option
# 3) 날짜 INPUT (React controlled — 직접 value 설정 불가):
#    JS nativeInputValueSetter 방식:
nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
).set
nativeInputValueSetter.call(input, 'YYYY.MM.DD')
input.dispatchEvent(new Event('input', {bubbles: true}))
input.dispatchEvent(new Event('change', {bubbles: true}))
input.blur()
```

---

## 6. inject_draft.py — 승인 글 직접 Excel 삽입

```python
# 상단 변수만 채워서 실행
TITLE = "제목"
BODY = """본문 (마커 포함)"""
TAGS = ["원어민강사", ..., "서이추", "서이추환영"]
IMAGE_KEYWORDS = ["키워드1", "키워드2"]
KEYWORD = "메인키워드"
ACCOUNT_ID = "bridge"

# 실행하면 drafts/draft_queue.xlsx에 "승인" 상태로 자동 삽입
# → "Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 inject_draft.py
# → 이후 --publish-approved 실행
```

Excel 컬럼: 날짜 | 키워드 | 제목 | 서론 | 본문 | 태그 | 이미지키워드 | 상태 | 계정ID

---

## 7. 글쓰기 규칙 v6.6 요약

### 글자수
- 최소: 1,500자 (공백 제외) — 미만 발행 불가
- 목표: 1,600자 / 권장: 2,000자+ / 채용 실무: 2,000~2,500자

### 출력 순서 (필수)
```
제목 → 서론 → 본문1 → 본문2 → [확장섹션 글자수 부족시만] → 본문3 → 결론
→ 내부 백링크 2개 (결론 직후 필수)
→ 에이전시 섹션 (100자 이내 2~3문장)
→ ⓒ 무단 전재 및 재배포 금지 / 중요 내용은 사실 확인 후 시행바랍니다
→ #태그들 #서이추 #서이추환영
```

### 절대 금지
- 마침표 전면 금지 (본문·서론·결론·부제목·태그·저작권 — 전 영역)
- 마크다운 기호 금지: `# * - | > \``
- 비자명 직접 언급 금지 (E-2 등)
- 나열·목록 금지 (문장 속 자연 삽입만)
- AI 생성 패턴: 동일 길이 단락 / 첫째둘째셋째 / 소제목 5개+ 정형 구조
- 사례 수치·상황 재사용 금지 (매 포스팅 완전 교체)

### 태그 구조
- 1~3번 고정: `#원어민강사 #원어민채용 #원어민구인`
- 끝 2개 고정: `#서이추 #서이추환영`
- 총 11~13개

### v6.6 vs v6.3.1 변경점
| 항목 | v6.3.1 | v6.6 |
|------|--------|------|
| 내부 백링크 | 없음 | 결론 직후 2개 필수 |
| 저작권 | "중요내용은" | "중요 **내용은**" (공백 추가) |
| 목표 글자수 | 1,800 | 1,600 (2,000 권장) |

---

## 8. Teast 구인공고 자동화

```
파일: tools/_teast_build_post.py
런처: scripts/teast_post.bat
조용한 실행: scripts/teast_post_silent.vbs (콘솔 팝업 없음)
```

포맷:
- 급여 표기: `2,60m` 형식 (2,600,000원)
- 고정 인트로 문단 (매 포스팅 상단)
- 고정 푸터 (매 포스팅 하단)
- '광고' 키워드 포스팅: 규칙 다름 (MEMORY.md 확인)

---

## 9. 배포게이트 (tools/deploy_gate.py)

```
1단계: 터미널 3분(180초) 대기
  → 화살표 키 메뉴: 1)Yes  2)Yes(8시간 스킵)  3)No
  → 숫자키 1/2/3 또는 화살표+Enter 지원
2단계: 무응답 시 텔레그램 알림 발송
```

---

## 10. bridge_prompt_ui.html (이미지 프롬프트 생성기)

```
경로: Q:/Claudework/bridge base/bridge_prompt_ui.html
ImageFX URL: labs.google/fx/tools/image-fx
```

구성:
- COMPOSITION: wide environmental 위주 12개 구도
- BOKEH: 자연스러운 심도 (극단 블러 제거)
- STUDENTS_EARLY/MIDDLE: 한국인 학생만 (외국인 제거)
- 프롬프트: FOREGROUND/BACKGROUND 분리 없이 통합 자연 장면
- 우측 패널: 한글 설명 8항목
- 아이콘: bridge_prompt.ico (보라-파랑, 카메라+하트+별, 16/24/32/48px)

---

## 11. 세션 기억 시스템 (3중 레이어)

| 레이어 | 파일 | 내용 |
|--------|------|------|
| 1 | `.claude/session_log.md` | 세션간 인계 (최근 5세션) |
| 2 | `tools/bridge_memory.db` | SQLite 영구 저장 (UserPrompt/ToolUse/Stop) |
| 3 | `tools/session_writer.py` | Stop 시 자동 요약 생성 |

hooks (settings.json):
- UserPromptSubmit → `bridge_memory.py --event user_prompt`
- PostToolUse → `bridge_memory.py --event post_tool`
- Stop → `bridge_memory.py --event stop`

검색: `python tools/bridge_memory.py search <키워드>`
상태: `python tools/bridge_memory.py --status`

---

## 12. 네이버 계정 정보

- naver_id: bridgejobkr
- blog_id: bridgejob
- 비밀번호: BRIDGE_NAVER_PW 환경변수 (절대 하드코딩 금지)
- 쿠키 경로: `Q:/Claudework/ClaudeBlog/logs/naver_cookies.json` (절대경로 필수)
