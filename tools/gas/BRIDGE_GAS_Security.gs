/**
 * BRIDGE ATS — Google Apps Script 보안 레이어
 * 버전: 1.0 (2026-04-07)
 *
 * 설치 위치: Google Sheets → 확장 프로그램 → Apps Script
 * 적용 대상: "접수시 입력" 스프레드시트 (기존 GAS 스크립트 보강)
 *
 * 3계층 시트 구조:
 *   Raw DB (원본) — 관리자만 접근, 폼 제출 원본 그대로
 *   State DB (상태) — 관리자만, 처리 상태/메모/분류
 *   View DB (배포) — PII 마스킹, 외부 공유 가능
 *
 * 사용자 액션 (1회):
 *   1. Google Sheets → 확장 프로그램 → Apps Script
 *   2. 이 파일 내용 전체 복사-붙여넣기
 *   3. CONFIG 상수의 시트명을 실제 시트명으로 수정
 *   4. setupTriggers() 함수 1회 실행
 *   5. 트리거 탭에서 onFormSubmit 트리거 확인
 */

// ═══════════════════════════════════════════════════
// 설정 — 시트명 매핑 (실제 시트명에 맞게 수정)
// ═══════════════════════════════════════════════════
const CONFIG = {
  RAW_SHEET:   "Form",           // 기존 폼 데이터 원본 탭
  STATE_SHEET: "New",            // 기존 처리 상태 탭
  VIEW_SHEET:  "View",           // 신규 생성 — PII 마스킹 뷰
  BACKUP_SHEET:"Backup",         // 자동 백업 접두어
  ADMIN_EMAIL: "bridgejobkr@gmail.com",
  LOG_SHEET:   "SystemLog",
};

// PII 컬럼 인덱스 (0-based, 실제 시트에 맞게 수정)
const PII_COLUMNS = {
  name:    1,    // B열
  email:   3,    // D열
  phone:   4,    // E열
  kakao:   5,    // F열
  address: null, // 없으면 null
};


// ═══════════════════════════════════════════════════
// 1. 폼 제출 트리거 — 중복 필터 + UID 발급
// ═══════════════════════════════════════════════════
function onFormSubmit(e) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const rawSheet = ss.getSheetByName(CONFIG.RAW_SHEET);
    if (!rawSheet) { logEvent("ERROR", "RAW_SHEET not found: " + CONFIG.RAW_SHEET); return; }

    const row = e.range.getRow();
    const values = rawSheet.getRange(row, 1, 1, rawSheet.getLastColumn()).getValues()[0];

    // 이메일 추출 (PII_COLUMNS.email 위치)
    const email = (values[PII_COLUMNS.email] || "").toString().trim().toLowerCase();

    // 중복 체크 — 같은 이메일 이미 접수 여부
    if (email && isDuplicate(rawSheet, email, PII_COLUMNS.email, row)) {
      logEvent("DUPLICATE_BLOCKED", "Row " + row + ": " + email.substring(0, 3) + "***");
      markDuplicate(rawSheet, row);
      return;
    }

    // UID 발급 (타임스탬프 + 4자리 랜덤)
    const uid = generateUID();
    rawSheet.getRange(row, rawSheet.getLastColumn() + 1).setValue(uid);

    // State DB에 상태 행 추가
    syncToStateSheet(ss, uid, values, row);

    // View DB에 PII 마스킹 행 추가
    syncToViewSheet(ss, uid, values);

    // 관리자 알림
    sendAdminNotification(uid, values);

    // 접수 안내메일 (지원자에게)
    sendConfirmationEmail(email, uid);

    logEvent("NEW_SUBMISSION", "UID: " + uid + ", Row: " + row);

  } catch (error) {
    logEvent("ERROR", "onFormSubmit: " + error.message);
    // 에러여도 프로세스 중단 금지 — 로그만 기록
  }
}


// ═══════════════════════════════════════════════════
// 2. 중복 검사
// ═══════════════════════════════════════════════════
function isDuplicate(sheet, email, colIndex, currentRow) {
  if (!email) return false;
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return false;
  const data = sheet.getRange(2, colIndex + 1, lastRow - 1, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    if (i + 2 === currentRow) continue; // 자기 자신 스킵
    if (data[i][0].toString().trim().toLowerCase() === email) return true;
  }
  return false;
}

function markDuplicate(sheet, row) {
  const lastCol = sheet.getLastColumn();
  const cell = sheet.getRange(row, lastCol + 1);
  cell.setValue("DUPLICATE");
  cell.setBackground("#ffcccc");
}


// ═══════════════════════════════════════════════════
// 3. UID 생성
// ═══════════════════════════════════════════════════
function generateUID() {
  const ts = Utilities.formatDate(new Date(), "Asia/Seoul", "yyMMddHHmm");
  const rand = Math.floor(1000 + Math.random() * 9000);
  return "BRG-" + ts + "-" + rand;
}


// ═══════════════════════════════════════════════════
// 4. PII 마스킹 → View DB 동기화
// ═══════════════════════════════════════════════════
function syncToViewSheet(ss, uid, values) {
  let viewSheet = ss.getSheetByName(CONFIG.VIEW_SHEET);
  if (!viewSheet) {
    viewSheet = ss.insertSheet(CONFIG.VIEW_SHEET);
    viewSheet.appendRow(["UID", "Timestamp", "(원본 헤더 추가 필요)"]);
  }

  const piiSet = new Set(Object.values(PII_COLUMNS).filter(v => v !== null));
  const masked = values.map(function(val, i) {
    if (piiSet.has(i) && val) {
      return maskPII(val.toString(), i);
    }
    return val;
  });

  viewSheet.appendRow([uid].concat(masked));
}

function maskPII(value, colIndex) {
  if (colIndex === PII_COLUMNS.name) {
    return value.charAt(0) + "***";
  }
  if (colIndex === PII_COLUMNS.email) {
    const parts = value.split("@");
    return parts[0].charAt(0) + "***@" + (parts[1] || "");
  }
  if (colIndex === PII_COLUMNS.phone) {
    return value.replace(/(\d{3})[-.]?(\d{4})[-.]?(\d{4})/, "$1-****-$3");
  }
  return "***";
}


// ═══════════════════════════════════════════════════
// 5. State DB 동기화
// ═══════════════════════════════════════════════════
function syncToStateSheet(ss, uid, values, rawRow) {
  const stateSheet = ss.getSheetByName(CONFIG.STATE_SHEET);
  if (!stateSheet) return;

  stateSheet.appendRow([
    uid,
    new Date(),
    "NEW",   // 초기 상태
    "",      // 메모
    rawRow,  // 원본 행 참조
  ]);
}


// ═══════════════════════════════════════════════════
// 6. 관리자 알림 + 접수 안내메일
// ═══════════════════════════════════════════════════
function sendAdminNotification(uid, values) {
  const name  = sanitize(values[PII_COLUMNS.name]  || "이름없음");
  const email = sanitize(values[PII_COLUMNS.email] || "");

  MailApp.sendEmail({
    to: CONFIG.ADMIN_EMAIL,
    subject: "[BRIDGE] 신규 접수 — " + uid,
    htmlBody: [
      "<h3>새 지원자 접수</h3>",
      "<p><strong>UID:</strong> " + uid + "</p>",
      "<p><strong>이름:</strong> " + name + "</p>",
      "<p><strong>이메일:</strong> " + email + "</p>",
      "<p><strong>접수시간:</strong> " + new Date().toLocaleString("ko-KR", {timeZone: "Asia/Seoul"}) + "</p>",
    ].join(""),
  });
}

function sendConfirmationEmail(email, uid) {
  if (!email) return;

  MailApp.sendEmail({
    to: email,
    subject: "[BRIDGE] Application Received — Thank you!",
    htmlBody: [
      "<p>Dear Applicant,</p>",
      "<p>Thank you for your application to BRIDGE Recruitment.</p>",
      "<p>Your application ID is: <strong>" + uid + "</strong></p>",
      "<p>We will review your application and get back to you shortly.</p>",
      "<br>",
      "<p>Best regards,<br><strong>BRIDGE Recruitment Team</strong></p>",
    ].join(""),
  });
}


// ═══════════════════════════════════════════════════
// 7. 자동 백업 (매일 자정 트리거)
// ═══════════════════════════════════════════════════
function dailyBackup() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const rawSheet = ss.getSheetByName(CONFIG.RAW_SHEET);
    if (!rawSheet) return;

    const today = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyyMMdd");
    const backupName = CONFIG.BACKUP_SHEET + "_" + today;

    // 기존 백업 시트 삭제 (같은 날짜)
    const existing = ss.getSheetByName(backupName);
    if (existing) ss.deleteSheet(existing);

    // 복사
    const backup = rawSheet.copyTo(ss);
    backup.setName(backupName);

    // 30일 이전 백업 삭제
    const sheets = ss.getSheets();
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 30);
    const cutoffStr = Utilities.formatDate(cutoff, "Asia/Seoul", "yyyyMMdd");

    sheets.forEach(function(s) {
      if (s.getName().startsWith(CONFIG.BACKUP_SHEET + "_")) {
        const dateStr = s.getName().replace(CONFIG.BACKUP_SHEET + "_", "");
        if (dateStr < cutoffStr) {
          ss.deleteSheet(s);
        }
      }
    });

    logEvent("BACKUP", "Daily backup created: " + backupName);
  } catch (error) {
    logEvent("ERROR", "dailyBackup: " + error.message);
  }
}


// ═══════════════════════════════════════════════════
// 8. 시스템 로그
// ═══════════════════════════════════════════════════
function logEvent(type, message) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let logSheet = ss.getSheetByName(CONFIG.LOG_SHEET);
    if (!logSheet) {
      logSheet = ss.insertSheet(CONFIG.LOG_SHEET);
      logSheet.appendRow(["Timestamp", "Type", "Message"]);
    }
    logSheet.appendRow([new Date(), type, message]);

    // 로그 1000행 초과 시 오래된 것 삭제
    if (logSheet.getLastRow() > 1000) {
      logSheet.deleteRows(2, logSheet.getLastRow() - 500);
    }
  } catch (e) {
    // 로그 실패는 무시
  }
}


// ═══════════════════════════════════════════════════
// 9. 트리거 자동 설정 (1회 실행)
// ═══════════════════════════════════════════════════
function setupTriggers() {
  // 기존 dailyBackup 트리거 제거
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === "dailyBackup") {
      ScriptApp.deleteTrigger(t);
    }
  });

  // 매일 자정 백업
  ScriptApp.newTrigger("dailyBackup")
    .timeBased()
    .everyDays(1)
    .atHour(0)
    .create();

  Logger.log("Triggers configured: dailyBackup @ 00:00 KST");
}


// ═══════════════════════════════════════════════════
// 10. 입력값 Sanitization (XSS/Injection 방지)
// ═══════════════════════════════════════════════════
function sanitize(input) {
  if (typeof input !== "string") return input;
  return input
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;")
    .replace(/'/g,  "&#39;")
    .replace(/\\/g, "&#92;")
    .trim();
}


// ═══════════════════════════════════════════════════
// 11. Web App 엔드포인트 (향후 외부 연동용 뼈대)
// ═══════════════════════════════════════════════════
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    // 향후 webhook 수신 등에 사용 (여기서 처리)
    return ContentService.createTextOutput(
      JSON.stringify({ status: "ok" })
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(
      JSON.stringify({ status: "error", message: error.message })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(
    JSON.stringify({ status: "ok", service: "BRIDGE ATS GAS", version: "1.0" })
  ).setMimeType(ContentService.MimeType.JSON);
}
