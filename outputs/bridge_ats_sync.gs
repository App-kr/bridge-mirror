/**
 * bridge_ats_sync.gs — BRIDGE ATS Google Apps Script 확장
 *
 * 목적: New 시트 완료 행 → Source 시트 이동 + DB 동기화
 * 설치: Google Apps Script 에디터에서 수동 추가
 *
 * ★ 기존 함수 수정 금지:
 *   - onFormSubmit
 *   - insertIntoWaitSheet
 *   - translateToKoreanDynamically
 *   - recoverMissingData
 */

// ── 설정 ────────────────────────────────────────────────────────────────────
const CONFIG = {
  SPREADSHEET_ID: PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID'),
  NEW_SHEET_NAME: 'New',
  SOURCE_SHEET_NAME: 'Source',
  API_BASE: 'https://api.bridgejob.co.kr',
  API_KEY: PropertiesService.getScriptProperties().getProperty('BRIDGE_API_KEY'),
  COMPLETED_STATUSES: ['completed', 'hired', 'placed'],
};

/**
 * syncNewToSource — New 시트의 완료된 행을 Source 시트로 이동
 *
 * 동작:
 * 1. New 시트에서 status가 완료/채용/배치인 행 탐색
 * 2. Source 시트 마지막 행에 append
 * 3. New 시트에서 해당 행 취소선 적용 (soft delete)
 *
 * 트리거: 수동 메뉴 또는 일일 1회 시간 트리거
 */
function syncNewToSource() {
  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const newSheet = ss.getSheetByName(CONFIG.NEW_SHEET_NAME);
  const sourceSheet = ss.getSheetByName(CONFIG.SOURCE_SHEET_NAME);

  if (!newSheet || !sourceSheet) {
    Logger.log('ERROR: Sheet not found');
    return;
  }

  const data = newSheet.getDataRange().getValues();
  if (data.length <= 1) return; // header only

  const header = data[0];
  // status 컬럼 인덱스 찾기 (보통 마지막 근처)
  const statusIdx = header.findIndex(h =>
    String(h).toLowerCase().includes('status') ||
    String(h).toLowerCase().includes('stage')
  );

  if (statusIdx === -1) {
    Logger.log('WARNING: status/stage column not found in New sheet');
    return;
  }

  let movedCount = 0;

  // 역순으로 처리 (행 삭제 시 인덱스 밀림 방지)
  for (let i = data.length - 1; i >= 1; i--) {
    const row = data[i];
    const status = String(row[statusIdx] || '').toLowerCase().trim();

    if (CONFIG.COMPLETED_STATUSES.includes(status)) {
      // Source 시트에 append
      sourceSheet.appendRow(row);

      // New 시트에서 취소선 적용 (soft delete — 물리 삭제 금지)
      const range = newSheet.getRange(i + 1, 1, 1, row.length);
      range.setFontLine('line-through');
      range.setFontColor('#999999');

      movedCount++;
    }
  }

  Logger.log(`syncNewToSource: ${movedCount} rows moved to Source`);

  if (movedCount > 0) {
    SpreadsheetApp.getUi().alert(`${movedCount}건이 Source 시트로 이동되었습니다.`);
  }
}

/**
 * backupToLocalDB — Sheet 데이터를 BRIDGE 서버 API로 POST (선택사항)
 *
 * 동작:
 * 1. New 시트 전체 데이터를 JSON으로 변환
 * 2. POST /api/sync/sheet-to-db 엔드포인트로 전송
 * 3. API key 인증
 *
 * ★ 이 함수는 서버 /api/sync/sheet-to-db 엔드포인트 구현 후 활성화
 */
function backupToLocalDB() {
  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const newSheet = ss.getSheetByName(CONFIG.NEW_SHEET_NAME);

  if (!newSheet) {
    Logger.log('ERROR: New sheet not found');
    return;
  }

  if (!CONFIG.API_KEY) {
    Logger.log('ERROR: BRIDGE_API_KEY not set in script properties');
    return;
  }

  const data = newSheet.getDataRange().getValues();
  if (data.length <= 1) return;

  const header = data[0];
  const rows = data.slice(1).map(row => {
    const obj = {};
    header.forEach((h, i) => {
      obj[String(h).trim()] = row[i];
    });
    return obj;
  });

  const payload = {
    source: 'google_sheet',
    sheet_name: CONFIG.NEW_SHEET_NAME,
    timestamp: new Date().toISOString(),
    rows: rows,
  };

  try {
    const response = UrlFetchApp.fetch(`${CONFIG.API_BASE}/api/sync/sheet-to-db`, {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'X-Admin-Key': CONFIG.API_KEY,
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    });

    const code = response.getResponseCode();
    const body = response.getContentText();

    if (code === 200 || code === 201) {
      Logger.log(`backupToLocalDB: ${rows.length} rows synced successfully`);
    } else {
      Logger.log(`backupToLocalDB FAILED: HTTP ${code} — ${body}`);
    }
  } catch (e) {
    Logger.log(`backupToLocalDB ERROR: ${e.message}`);
  }
}

/**
 * 커스텀 메뉴 등록 — 스프레드시트 열기 시 자동 추가
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('BRIDGE ATS')
    .addItem('New → Source 이동', 'syncNewToSource')
    .addItem('DB 동기화 (선택)', 'backupToLocalDB')
    .addToUi();
}

/**
 * 일일 시간 트리거 설치 (최초 1회 수동 실행)
 */
function installDailyTrigger() {
  // 기존 syncNewToSource 트리거 제거
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(t => {
    if (t.getHandlerFunction() === 'syncNewToSource') {
      ScriptApp.deleteTrigger(t);
    }
  });

  // 매일 오전 9시 실행
  ScriptApp.newTrigger('syncNewToSource')
    .timeBased()
    .everyDays(1)
    .atHour(9)
    .create();

  Logger.log('Daily trigger installed: syncNewToSource at 9 AM');
}
