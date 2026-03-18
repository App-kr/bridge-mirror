// ============================================================
// BRIDGE Google Apps Script — 완성본 v3
// 2026-03-17 컬럼 전체 확인 완료
// 2026-03-18 v2: 버그 수정 (FIX-1~6)
// 2026-03-18 v3: 원본 xlsx 직접 파싱 — SRC/NEW 전체 컬럼 재검증
//   CRITICAL FIX: Form 시트 col 15 = ARC holders (기존엔 Passport로 잘못 기재)
//   → col 15부터 전체 1칸 오프셋 오류 수정
//   → NEW 시트 AM(39) = Passport 추가 (기존 누락)
//   → Experience(Form col 23) 매핑 복원
//   → 배열 크기 49→50, 폼 읽기 38→40 컬럼
// ============================================================

const CONFIG = {
  SHEET_SOURCE: 'Form',   // ← 실제 탭명: "Form" (구글폼 원본)
  SHEET_NEW:    'New',
  SHEET_CLIENT: 'Client',

  NEW_HEADER_ROWS: 2,
  NEW_DATA_START:  3,

  NUMBER_START: 10001,

  COLOR_NEW:     '#FFFDE7',  // 신규 접수 — 연노랑
  COLOR_HIRED:   '#E8F5E9',  // 채용완료 — 연녹
  COLOR_WAITING: '#FFF3E0',  // 취업대기 — 연주황

  // ── Form 시트 컬럼 (구글폼 원본, 1-indexed) ──
  // 2026-03-18 실측: xlsx sharedStrings 직접 파싱으로 확인
  SRC: {
    TIMESTAMP:   1,   // A — 타임스탬프
    EMAIL:       2,   // B — 이메일 주소
    HOW_TO:      3,   // C — How to (경로)
    ATTACH:      4,   // D — Attach your files
    FULLNAME:    5,   // E — Full name
    NATIONALITY: 6,   // F — Nationality
    ANCESTRY:    7,   // G — Family Ancestry Background
    DOB:         8,   // H — Date of Birth
    GENDER:      9,   // I — Gender
    LOCATION:    10,  // J — Current Location
    EDUCATION:   11,  // K — Educational Background
    MAJOR:       12,  // L — Major
    CERT:        13,  // M — Certification
    EVISA:       14,  // N — E visa
    ARC:         15,  // O — ARC holders  ← 이전 버전에서 PASSPORT로 잘못 표기
    PASSPORT:    16,  // P — Passport
    CRIMINAL:    17,  // Q — Criminal Record
    DOCS:        18,  // R — Document Status
    START_DATE:  19,  // S — Start date
    TARGET:      20,  // T — Target
    AREA_PREFS:  21,  // U — Area prefs
    JOB_PREFS:   22,  // V — Job prefs (Notes)
    EXPERIENCE:  23,  // W — Experience (경력 텍스트: "over 4 year" 등)
    EMPLOYMENT:  24,  // X — Employment (한국 근무처)
    REFERENCE:   25,  // Y — Reference
    CURR_SAL:    26,  // Z — Current salary
    DESIRED_SAL: 27,  // AA — Desired salary
    MARITAL:     28,  // AB — Marital Status
    DEPENDENTS:  29,  // AC — Dependents Pets
    HOUSING:     30,  // AD — Housing
    PERSONAL:    31,  // AE — Personal Considerations
    RELIGION:    32,  // AF — Religion
    HEALTH:      33,  // AG — Health Information
    CRIMINAL_KR: 34,  // AH — Criminal Record Check
    INTV_TIME:   35,  // AI — Interview time
    KAKAO:       36,  // AJ — KakaoTalk
    MOBILE:      37,  // AK — Mobile Phone
    AGREEMENT:   38,  // AL — Agreement
    FACTS:       39,  // AM — Facts
    MEMO:        40,  // AN — 메모
  },

  // ── New 시트 컬럼 (운영 관리, 1-indexed) ──
  // 2026-03-18 실측: A~AX = 50열 확인
  NEW: {
    EMAIL:       1,   // A — 이메일 주소
    NAME:        2,   // B — Full name
    PHOTO:       3,   // C — Photo (수동)
    NUMBER:      4,   // D — No (번호, 자동부여)
    ARC:         5,   // E — ARC holders
    NATIONALITY: 6,   // F — Nationality
    ANCESTRY:    7,   // G — Family Ancestry Background
    DOB:         8,   // H — Date of Birth
    GENDER:      9,   // I — Gender
    LOCATION:    10,  // J — Current Location
    START:       11,  // K — Start date
    TARGET:      12,  // L — Target
    AREA:        13,  // M — Area prefs
    REFERENCE:   14,  // N — Reference
    EXPERIENCE:  15,  // O — Experience (경력)
    EMPLOYMENT:  16,  // P — Employment (한국 근무처)
    JOB_PREFS:   17,  // Q — Job prefs (선호사항/리크루터인터뷰)
    INTERVIEW:   18,  // R — Interview (수동)
    APPLY:       19,  // S — Apply (수동)
    CURR_SAL:    20,  // T — Current salary
    DESIRED_SAL: 21,  // U — Desired salary
    INTV_TIME:   22,  // V — Interview time
    DEGREE:      23,  // W — Degree
    MAJOR:       24,  // X — Major
    CERT:        25,  // Y — Certification
    DOCS:        26,  // Z — Documents
    HEALTH:      27,  // AA — Health Information
    PERSONAL:    28,  // AB — Personal Considerations (타투)
    PIERCINGS:   29,  // AC — piercings
    DEPENDENTS:  30,  // AD — Dependents Pets
    MARITAL:     31,  // AE — Marital Status
    HOUSING:     32,  // AF — Housing
    RELIGION:    33,  // AG — Religion
    EVISA:       34,  // AH — E visa
    KAKAO:       35,  // AI — KakaoTalk
    MOBILE:      36,  // AJ — Mobile Phone (PII — 관리자 내부용)
    CRIMINAL:    37,  // AK — Criminal Record
    CRIMINAL_KR: 38,  // AL — Criminal Record in Korea
    PASSPORT:    39,  // AM — Passport (여권)       ← 이전 버전 누락
    AGREEMENT:   40,  // AN — Agreement (동의)
    FACTS:       41,  // AO — Facts (사실)
    HOW_TO:      42,  // AP — How to (경로)
    TIMESTAMP:   43,  // AQ — 타임스탬프
    HIRED_AT:    44,  // AR — 채용처 (수동)
    WAGE:        45,  // AS — 임금 (수동)
    START_MONTH: 46,  // AT — 개시월 (수동)
    HOUSING2:    47,  // AU — 숙박 (수동)
    COST:        48,  // AV — 비용 (수동)
    PROCESS:     49,  // AW — 처리 (수동)
    PAST_MEMO:   50,  // AX — 과거메모 (수동)
  },
};


// ============================================================
// 메인 트리거 — 폼 제출 시 자동 실행
// ============================================================
function onFormSubmit(e) {
  // ── [FIX-2] LockService: 동시 제출 race condition 방지 ──
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000); // 최대 15초 대기

    const ss  = SpreadsheetApp.getActiveSpreadsheet();
    const src = ss.getSheetByName(CONFIG.SHEET_SOURCE);
    const nw  = ss.getSheetByName(CONFIG.SHEET_NEW);

    if (!src || !nw) {
      Logger.log('ERROR: 시트를 찾을 수 없음 — 탭 이름 확인 필요 (Form / New)');
      return;
    }

    // ── [FIX-3] e.range.getRow(): 이벤트 정확한 행 사용 (getLastRow race 방지) ──
    const submittedRow = e.range.getRow();
    // Form 시트: 40컬럼 (A~AN) — 2026-03-18 실측
    const form         = src.getRange(submittedRow, 1, 1, 40).getValues()[0];
    const nextNum      = getNextNumber(nw);
    const newRow       = buildNewRow(form, nextNum);

    // New 시트 데이터 최상단 (3행)에 삽입
    nw.insertRowBefore(CONFIG.NEW_DATA_START);
    const range = nw.getRange(CONFIG.NEW_DATA_START, 1, 1, newRow.length);
    range.setValues([newRow]);

    // ── [FIX-4] copyFormatToRange 먼저 → setBackground 마지막 (색상 덮어쓰기 방지) ──
    if (nw.getLastRow() > CONFIG.NEW_DATA_START) {
      const templateRange = nw.getRange(CONFIG.NEW_DATA_START + 1, 1, 1, newRow.length);
      templateRange.copyFormatToRange(
        nw, 1, newRow.length,
        CONFIG.NEW_DATA_START, CONFIG.NEW_DATA_START
      );
    }
    range.setBackground(CONFIG.COLOR_NEW); // 서식 복사 후 마지막에 적용

    // [FIX-6] Utilities.htmlEscape() — HTML 컨텍스트 사용 시 XSS 방지
    const safeEmail = Utilities.htmlEscape(String(form[CONFIG.SRC.EMAIL-1] ?? ''));
    Logger.log(`✅ 번호 ${nextNum} | 행 ${submittedRow} | ${safeEmail}`);
  } catch (err) {
    Logger.log('ERROR: ' + err.message);
  } finally {
    lock.releaseLock();
  }
}


// ============================================================
// 5자리 번호 자동 생성
// ============================================================
function getNextNumber(sheet) {
  const col      = CONFIG.NEW.NUMBER;
  const startRow = CONFIG.NEW_DATA_START;
  const lastRow  = sheet.getLastRow();

  if (lastRow < startRow) return CONFIG.NUMBER_START;

  const values  = sheet.getRange(startRow, col, lastRow - startRow + 1, 1).getValues();
  const numbers = values.flat()
    .filter(v => v && !isNaN(v))
    .map(v => parseInt(v));

  if (numbers.length === 0) return CONFIG.NUMBER_START;

  const maxNum = Math.max(...numbers);
  return maxNum < 10000 ? CONFIG.NUMBER_START : maxNum + 1;
}


// ============================================================
// Form → New 매핑 (2026-03-18 xlsx 실측 기준 완전 수정)
// ============================================================
function buildNewRow(form, number) {
  const s = CONFIG.SRC;
  const n = CONFIG.NEW;
  // New 시트: 50열 (A~AX)
  const row = new Array(50).fill('');

  // [FIX-5] null/undefined/공백 안전 처리
  const get = (col) => {
    const v = form[col - 1];
    if (v === null || v === undefined) return '';
    return String(v).trim();
  };

  // ── 기본 정보 ──
  row[n.EMAIL      - 1] = get(s.EMAIL);
  row[n.NAME       - 1] = get(s.FULLNAME);
  // row[n.PHOTO   - 1] = ''; // 수동 — Drive URL
  row[n.NUMBER     - 1] = number;
  row[n.ARC        - 1] = get(s.ARC);         // Form O열(15): ARC holders
  row[n.NATIONALITY- 1] = get(s.NATIONALITY);
  row[n.ANCESTRY   - 1] = get(s.ANCESTRY);
  row[n.DOB        - 1] = get(s.DOB);
  row[n.GENDER     - 1] = get(s.GENDER);
  row[n.LOCATION   - 1] = get(s.LOCATION);

  // ── 근무 조건 ──
  row[n.START      - 1] = get(s.START_DATE);
  row[n.TARGET     - 1] = get(s.TARGET);
  row[n.AREA       - 1] = get(s.AREA_PREFS);

  // ── 경력/레퍼런스 ──
  row[n.REFERENCE  - 1] = get(s.REFERENCE);
  row[n.EXPERIENCE - 1] = get(s.EXPERIENCE);  // Form W열(23): Experience 텍스트
  row[n.EMPLOYMENT - 1] = get(s.EMPLOYMENT);  // Form X열(24): 한국 근무처

  // ── 리크루터 관리 ──
  row[n.JOB_PREFS  - 1] = get(s.JOB_PREFS);
  // INTERVIEW(R), APPLY(S) → 수동

  // ── 급여 ──
  row[n.CURR_SAL   - 1] = get(s.CURR_SAL);
  row[n.DESIRED_SAL- 1] = get(s.DESIRED_SAL);
  row[n.INTV_TIME  - 1] = get(s.INTV_TIME);

  // ── 학력 ──
  row[n.DEGREE     - 1] = get(s.EDUCATION);
  row[n.MAJOR      - 1] = get(s.MAJOR);
  row[n.CERT       - 1] = get(s.CERT);
  row[n.DOCS       - 1] = get(s.DOCS);

  // ── 개인 정보 ──
  row[n.HEALTH     - 1] = get(s.HEALTH);
  row[n.PERSONAL   - 1] = get(s.PERSONAL);
  // PIERCINGS: Form에 별도 컬럼 없음 (Personal에 포함)
  row[n.DEPENDENTS - 1] = get(s.DEPENDENTS);
  row[n.MARITAL    - 1] = get(s.MARITAL);
  row[n.HOUSING    - 1] = get(s.HOUSING);
  row[n.RELIGION   - 1] = get(s.RELIGION);

  // ── 비자/연락처 ──
  row[n.EVISA      - 1] = get(s.EVISA);       // Form N열(14): E visa
  row[n.KAKAO      - 1] = get(s.KAKAO);
  row[n.MOBILE     - 1] = get(s.MOBILE);       // PII — 관리자 내부용

  // ── 범죄/여권 ──
  row[n.CRIMINAL   - 1] = get(s.CRIMINAL);
  row[n.CRIMINAL_KR- 1] = get(s.CRIMINAL_KR);
  row[n.PASSPORT   - 1] = get(s.PASSPORT);    // Form P열(16): Passport

  // ── 동의/경로 ──
  row[n.AGREEMENT  - 1] = get(s.AGREEMENT);
  row[n.FACTS      - 1] = get(s.FACTS);
  row[n.HOW_TO     - 1] = get(s.HOW_TO);
  row[n.TIMESTAMP  - 1] = get(s.TIMESTAMP);

  // ── 채용 관리 컬럼 (수동) ──
  // HIRED_AT, WAGE, START_MONTH, HOUSING2, COST, PROCESS, PAST_MEMO → 빈칸

  return row;
}


// ============================================================
// 수동 실행 — 테스트용
// ============================================================
function testRun() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const nw = ss.getSheetByName(CONFIG.SHEET_NEW);
  const src = ss.getSheetByName(CONFIG.SHEET_SOURCE);

  Logger.log('=== BRIDGE Apps Script 테스트 ===');
  Logger.log('시트 목록: ' + ss.getSheets().map(s => s.getName()).join(', '));
  Logger.log('New 시트 마지막 행: ' + nw.getLastRow());
  Logger.log('Form 시트 마지막 행: ' + src.getLastRow());
  Logger.log('다음 부여 번호: ' + getNextNumber(nw));
  Logger.log('New 50열 / Form 40열 매핑 v3 활성');
}


// ============================================================
// 트리거 설치 — 최초 1회 실행
// ============================================================
function installTrigger() {
  // 기존 트리거 삭제
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));

  // 폼 제출 트리거 설치
  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onFormSubmit()
    .create();

  Logger.log('✅ 트리거 설치 완료');
}
