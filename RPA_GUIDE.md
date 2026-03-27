# Craigslist RPA 실행 가이드

## 빠른 시작 (1분)

```bash
# 1단계: Craigslist 계정 정보 입력
python auto_vault_setup.py

# 2단계: 테스트 실행 (광고 미리보기만)
python craigslist_auto_rpa.py --dry-run --limit 1
```

---

## 모드별 사용법

### 1. DRY-RUN 모드 ✅ **권장 (Selenium 불필요)**
광고 텍스트 미리보기 + PII 자동 제거 확인

```bash
python craigslist_auto_rpa.py --dry-run --limit 3
```

**필요한 것:**
- ✅ Python 표준 라이브러리
- ✅ .rpa_vault.json (auto_vault_setup.py로 생성)
- ✅ master.db

**시간:** 5초 이내
**위험도:** 안전 (실제 게시 없음)

---

### 2. GENERATE 모드 ✅ **권장 (Selenium 불필요)**
draft 데이터를 DB에 저장 (실제 게시 안 함)

```bash
python craigslist_auto_rpa.py --generate --limit 5
```

**필요한 것:**
- ✅ Python 표준 라이브러리
- ✅ .rpa_vault.json
- ✅ master.db

**시간:** 10초 이내
**위험도:** 안전 (DB 변경, 웹사이트 접근 안 함)

---

### 3. 실제 게시 모드 ⚠️ **수동 설정 필요**
Craigslist에 실제로 광고 게시

```bash
# 먼저 Selenium 설치
pip install selenium webdriver-manager

# 실행
python craigslist_auto_rpa.py --account gray --limit 1
```

**필요한 것:**
- ❌ Selenium (**pip install 필수**)
- ❌ ChromeDriver (자동 다운로드됨)
- ✅ .rpa_vault.json (Craigslist 계정)
- ✅ master.db

**시간:** 1-2분 (계정당)
**위험도:** 중간 (실제 웹사이트 접근)

---

## 계정 설정 (일회성)

```bash
# 대화형 설정 (모든 계정 한번에)
python auto_vault_setup.py

# 또는 특정 계정만 설정
python auto_vault_setup.py --account gray
```

**저장 위치:** `.rpa_vault.json` (현재 디렉토리)

**계정 목록:**
- `gray` - 회색 계정
- `green` - 초록 계정
- `brown` - 갈색 계정
- `purple` - 보라 계정

---

## 문제 해결

### "꺼진다" / 에러 발생
→ DRY-RUN 모드로 테스트:
```bash
python craigslist_auto_rpa.py --dry-run --limit 1
```

### Vault 파일을 찾을 수 없음
→ auto_vault_setup.py를 먼저 실행:
```bash
python auto_vault_setup.py
```

### Selenium 설치 실패
→ Python pip 환경 확인:
```bash
pip install selenium webdriver-manager -v
```

### 다른 에러
→ 상세 에러 메시지 확인:
```bash
python craigslist_auto_rpa.py --dry-run 2>&1
```

---

## 안전 기능

✅ **PII 자동 제거**
- 업체명, 주소, 전화, 이메일 → 자동 제거
- 광고에 개인정보 절대 노출 안 함

✅ **파일 무결성**
- 프로그램 변조 감지
- 해킹 시도 차단

✅ **세션 바인딩**
- 계정당 중복 실행 방지
- 동시 게시 차단

---

## 권장 워크플로우

1. **준비** (1회)
   ```bash
   python auto_vault_setup.py
   ```

2. **테스트** (매 게시 전)
   ```bash
   python craigslist_auto_rpa.py --dry-run --limit 1
   ```

3. **Draft 생성**
   ```bash
   python craigslist_auto_rpa.py --generate --limit 5
   ```

4. **실제 게시** (Selenium 설치 후)
   ```bash
   pip install selenium webdriver-manager
   python craigslist_auto_rpa.py --account gray --limit 3
   ```

---

## 명령어 전체

```
--dry-run           텍스트만 출력 (게시 안 함)
--generate          Draft DB 저장 (게시 안 함)
--account NAME      계정 선택 (gray/green/brown/purple)
--limit N           최대 N건 게시
--headless          화면 없이 실행 (Selenium 필요)
--help              도움말 표시
```

**예시:**
```bash
python craigslist_auto_rpa.py --account gray --limit 1 --headless
```

---

**마지막 업데이트:** 2026-03-27
