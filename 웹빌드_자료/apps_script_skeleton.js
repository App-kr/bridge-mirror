// ============================================================
// BRIDGE Google Apps Script — 완성본 v2
// 2026-03-17 컬럼 전체 확인 완료
// 2026-03-18 버그 수정 (FIX-1~4):
//   FIX-1: O열 EXPERIENCE 중복매핑 제거 (경력연수 = 수동입력)
//   FIX-2: LockService 추가 (동시제출 race condition 방지)
//   FIX-3: e.range.getRow() 사용 (getLastRow() race 방지)
//   FIX-4: copyFormatToRange → setBackground 순서 수정 (색상 덮어쓰기 방지)
// ============================================================

const CONFIG = {
  SHEET_SOURCE: 'Source',
  SHEET_NEW:    'New',
  SHEET_CLIENT: 'Client',

  NEW_HEADER_ROWS: 2,
  NEW_DATA_START:  3,

  NUMBER_START: 10001,

  COLOR_NEW:     '#FFFDE7',  // 신규 접수 — 연노랑
  COLOR_HIRED:   '#E8F5E9',  // 채용완료 — 연녹
  COLOR_WAITING: '#FFF3E0',  // 취업대기 — 연주황

  // ── Source 시트 컬럼 (구글폼 원본, 1-indexed) ──
  SRC: {
    TIMESTAMP:   1,   // 타임스탬프
    EMAIL:       2,   // 이메일 주소
    HOW_TO:      3,   // How to (경로)
    ATTACH:      4,   // Attach your files
    FULLNAME:    5,   // Full name
    NATIONALITY: 6,   // Nationality
    ANCESTRY:    7,   // Family Ancestry Background
    DOB:         8,   // Date of Birth
    GENDER:      9,   // Gender
    LOCATION:    10,  // Current Location
    EDUCATION:   11,  // Educational Background
    MAJOR:       12,  // Major
    CERT:        13,  // Certification
    EVISA:       14,  // E visa
    PASSPORT:    15,  // Passport
    CRIMINAL:    16,  // Criminal Record
    DOCS:        17,  // Document Status
    START_DATE:  18,  // Start date
    TARGET:      19,  // Target
    AREA_PREFS:  20,  // Area prefs
    JOB_PREFS:   21,  // Job prefs
    EMPLOYMENT:  22,  // Employment (한국 경력)
    REFERENCE:   23,  // Reference
    CURR_SAL:    24,  // Current salary
    DESIRED_SAL: 25,  // Desired salary
    MARITAL:     26,  // Marital Status
    DEPENDENTS:  27,  // Dependents Pets
    HOUSING:     28,  // Housing
    PERSONAL:    29,  // Personal Considerations
    RELIGION:    30,  // Religion
    HEALTH:      31,  // Health Information
    CRIMINAL_KR: 32,  // Criminal Record in Korea
    INTV_TIME:   33,  // Interview time
    KAKAO:       34,  // KakaoTalk
    MOBILE:      35,  // Mobile Phone
    AGREEMENT:   36,  // Agreement
    FACTS:       37,  // Facts
    MEMO:        38,  // 메모
  },

  // ── New 시트 컬럼 (운영 관리, 1-indexed) ──
  // A=1 ~ AW=49 확인 완료
  NEW: {
    EMAIL:       1,   // A — 메 (이메일 주소)
    NAME:        2,   // B — 이 (Full name)
    PHOTO:       3,   // C — 사 (Photo — 수동)
    NUMBER:      4,   // D — 번 (번호 — 자동부여)
    ARC:         5,   // E — ARC holders
    NATIONALITY: 6,   // F — 국적
    ANCESTRY:    7,   // G — 배경
    DOB:         8,   // H — 나이
    GENDER:      9,   // I — 성별
    LOCATION:    10,  // J — 현재
    START:       11,  // K — 시작
    TARGET:      12,  // L — 대상
    AREA:        13,  // M — 지역
    REFERENCE:   14,  // N — 레퍼런스/근무처확인
    EXPERIENCE:  15,  // O — 경력
    EMPLOYMENT:  16,  // P — 한국 (Employment)
    JOB_PREFS:   17,  // Q — 선호사항/리크루터인터뷰
    INTERVIEW:   18,  // R — 지원한곳/인터뷰요청 (수동)
    APPLY:       19,  // S — 포지션제안/진행 (수동)
    CURR_SAL:    20,  // T — 현급
    DESIRED_SAL: 21,  // U — 희망
    INTV_TIME:   22,  // V — 시간
    DEGREE:      23,  // W — 학위
    MAJOR:       24,  // X — 전공
    CERT:        25,  // Y — 자격
    DOCS:        26,  // Z — 서류
    HEALTH:      27,  // AA — 건강
    PERSONAL:    28,  // AB — 타투
    PIERCINGS:   29,  // AC — 피어
    DEPENDENTS:  30,  // AD — 가족
    MARITAL:     31,  // AE — 결혼
    HOUSING:     32,  // AF — 숙소
    RELIGION:    33,  // AG — 종교
    EVISA:       34,  // AH — 비자
    KAKAO:       35,  // AI — 카톡
    MOBILE:      36,  // AJ — 핸폰 (PII — 관리자 내부용)
    CRIMINAL:    37,  // AK — 범죄
    CRIMINAL_KR: 38,  // AL — 국범
    AGREEMENT:   39,  // AM — 동의
    FACTS:       40,  // AN — 사실
    HOW_TO:      41,  // AO — 경로
    TIMESTAMP:   42,  // AP — 타임스탬프
    HIRED_AT:    43,  // AQ — 채용처 (수동)
    WAGE:        44,  // AR — 임금 (수동)
    START_MONTH: 45,  // AS — 개시월 (수동)
    HOUSING2:    46,  // AT — 숙박 (수동)
    COST:        47,  // AU — 비용 (수동)
    PROCESS:     48,  // AV — 처리 (수동)
    PAST_MEMO:   49,  // AW — 과거메모 (수동)
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
      Logger.log('ERROR: 시트를 찾을 수 없음 — 탭 이름 확인 필요');
      return;
    }

    // ── [FIX-3] e.range.getRow(): 이벤트 정확한 행 사용 (getLastRow race 방지) ──
    const submittedRow = e.range.getRow();
    const form         = src.getRange(submittedRow, 1, 1, 38).getValues()[0];
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

    Logger.log(`✅ 번호 ${nextNum} | 행 ${submittedRow} | ${form[CONFIG.SRC.EMAIL-1]}`);
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
// Source → New 매핑 (전체 컬럼 확인 완료)
// ============================================================
function buildNewRow(form, number) {
  const s = CONFIG.SRC;
  const n = CONFIG.NEW;
  const row = new Array(49).fill('');

  const get = (col) => form[col - 1] ?? '';

  // ── 기본 정보 ──
  row[n.EMAIL      - 1] = get(s.EMAIL);
  row[n.NAME       - 1] = get(s.FULLNAME);
  // row[n.PHOTO   - 1] = ''; // 수동 — 구글폼 첨부는 Drive URL로 처리
  row[n.NUMBER     - 1] = number;
  row[n.ARC        - 1] = get(s.EVISA);   // E visa → ARC 참고값
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
  // [FIX-1] O열(EXPERIENCE=경력연수)은 폼에 숫자 항목 없음 → 수동 입력, 빈칸 유지
  // row[n.EXPERIENCE - 1] = '';  // 수동 — 경력연수는 스프레드시트에서 직접 입력
  row[n.EMPLOYMENT - 1] = get(s.EMPLOYMENT);  // P열 — 한국 근무처 (텍스트)

  // ── 리크루터 관리 (수동) ──
  row[n.JOB_PREFS  - 1] = get(s.JOB_PREFS);
  // INTERVIEW, APPLY → 수동

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
  // PIERCINGS → Source에 별도 컬럼 없음, Personal에 포함된 경우 처리
  row[n.DEPENDENTS - 1] = get(s.DEPENDENTS);
  row[n.MARITAL    - 1] = get(s.MARITAL);
  row[n.HOUSING    - 1] = get(s.HOUSING);
  row[n.RELIGION   - 1] = get(s.RELIGION);

  // ── 비자/연락처 ──
  row[n.EVISA      - 1] = get(s.EVISA);
  row[n.KAKAO      - 1] = get(s.KAKAO);
  row[n.MOBILE     - 1] = get(s.MOBILE);   // PII — 관리자 내부용

  // ── 범죄기록 ──
  row[n.CRIMINAL   - 1] = get(s.CRIMINAL);
  row[n.CRIMINAL_KR- 1] = get(s.CRIMINAL_KR);

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
  Logger.log('Source 시트 마지막 행: ' + src.getLastRow());
  Logger.log('다음 부여 번호: ' + getNextNumber(nw));
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
