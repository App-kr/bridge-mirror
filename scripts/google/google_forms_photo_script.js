// ============================================
// Google Forms Photo Auto-Extract Apps Script
// bridgejob.co.kr - ESL Teacher Application
// ============================================
//
// 설치 방법 (1회만)
// ============================================
// 1. Google 스프레드시트 열기 (bridgejobkr@gmail.com)
// 2. 확장프로그램 > Apps Script
// 3. 기존 코드 전부 지우고 이 파일 전체 붙여넣기
// 4. 메뉴에서 setupTrigger 함수 선택 > 실행
// 5. Google 권한 승인 (Drive + Spreadsheet 접근)
// 6. 끝. 이후 Forms 제출마다 자동 실행
//
// 기존 행 일괄 처리:
//   메뉴에서 backfillPhotos 선택 > 실행
//
// 문제 발생 시:
//   Log 시트 확인 또는 restoreFromBackup(행번호) 실행
// ============================================

// ------------------------------------
// 설정
// ------------------------------------
var CONFIG = {
  SHEET_NAME: 'New',
  LOG_SHEET: 'Log',
  BACKUP_SHEET: 'Backup',
  ARCHIVE_FOLDER: 'Photo_Archive',
  ROW_HEIGHT: 80,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  LOG_RETENTION_DAYS: 30,
  FILE_ID_PATTERN: /^[a-zA-Z0-9_-]+$/,
  ALLOWED_MIME_PREFIX: 'image/',
  HEADER_PHOTO: ['Photo', 'photo', '사진'],
  HEADER_EMAIL: ['Email', 'email', '이메일', '이메일 주소'],
  HEADER_NAME: ['Full name', 'full name', 'Name', 'name', '이름', '성명']
};


// ============================================
// 1. 트리거 설정
// ============================================

/**
 * onFormSubmit 트리거 등록 (1회 실행)
 * 메뉴에서 이 함수를 선택하고 실행하세요.
 */
function setupTrigger() {
  // 기존 트리거 중복 방지
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'onFormSubmit') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit()
    .create();

  ensureSheets_();
  writeLog_('SETUP', '-', 'SUCCESS', 'Trigger registered');
  SpreadsheetApp.getUi().alert(
    'Setup Complete\n\n' +
    '- onFormSubmit 트리거 등록 완료\n' +
    '- Log/Backup 시트 준비 완료\n\n' +
    '이제 Forms 제출마다 자동으로 사진이 처리됩니다.'
  );
}


// ============================================
// 2. 핵심: onFormSubmit 트리거 핸들러
// ============================================

/**
 * Forms 제출 시 자동 실행
 * @param {Object} e - 이벤트 객체
 */
function onFormSubmit(e) {
  try {
    if (!e || !e.range) {
      writeLog_('SUBMIT', '-', 'SKIP', 'Invalid event object');
      return;
    }

    var sheet = e.range.getSheet();
    if (sheet.getName() !== CONFIG.SHEET_NAME) {
      return;
    }

    var row = e.range.getRow();
    var cols = detectColumns_(sheet);

    // 백업
    backupRow_(sheet, row);

    // Photo 처리
    processPhotoForRow_(sheet, row, cols);

  } catch (err) {
    writeLog_('SUBMIT', String(e && e.range ? e.range.getRow() : '?'),
      'ERROR', err.message + '\n' + err.stack);
  }
}


// ============================================
// 3. 사진 처리 로직
// ============================================

/**
 * 단일 행의 Photo 처리
 * @param {Sheet} sheet
 * @param {number} row
 * @param {Object} cols - {photo, email, name} 컬럼 인덱스(1-based)
 */
function processPhotoForRow_(sheet, row, cols) {
  var photoCell = sheet.getRange(row, cols.photo);
  var currentValue = photoCell.getValue();

  // 이미 값이 있으면 건드리지 않음
  if (currentValue !== '' && currentValue !== null && currentValue !== undefined) {
    writeLog_('PROCESS', String(row), 'SKIP', 'Photo cell already has value');
    return;
  }

  // Drive URL 추출 (Forms 파일 업로드 응답)
  var rawValue = String(photoCell.getDisplayValue() || sheet.getRange(row, cols.photo).getFormula() || '');

  // 해당 행 전체에서 Drive URL 탐색 (Forms가 URL을 직접 넣는 경우)
  if (!rawValue || !rawValue.match(/drive\.google\.com|docs\.google\.com/)) {
    var rowData = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
    rawValue = findDriveUrl_(rowData, cols.photo - 1);
  }

  if (!rawValue || rawValue === '') {
    photoCell.setValue('No Photo');
    sheet.setRowHeight(row, CONFIG.ROW_HEIGHT);
    writeLog_('PROCESS', String(row), 'NO_PHOTO', 'No Drive URL found');
    return;
  }

  // 파일 ID 파싱
  var fileId = extractFileId_(rawValue);
  if (!fileId) {
    photoCell.setValue('No Photo');
    sheet.setRowHeight(row, CONFIG.ROW_HEIGHT);
    writeLog_('PROCESS', String(row), 'FAIL', 'Cannot parse file ID from: ' + rawValue);
    return;
  }

  // 파일 ID 정규식 검증
  if (!CONFIG.FILE_ID_PATTERN.test(fileId)) {
    writeLog_('PROCESS', String(row), 'FAIL', 'Invalid file ID pattern: ' + fileId);
    photoCell.setValue('No Photo');
    return;
  }

  // Drive 파일 검증
  var file;
  try {
    file = DriveApp.getFileById(fileId);
  } catch (err) {
    writeLog_('PROCESS', String(row), 'FAIL', 'Cannot access file: ' + fileId);
    photoCell.setValue('No Photo');
    return;
  }

  // MIME 타입 검증 (이미지만)
  var mimeType = file.getMimeType();
  if (!mimeType || mimeType.indexOf(CONFIG.ALLOWED_MIME_PREFIX) !== 0) {
    writeLog_('PROCESS', String(row), 'REJECT', 'Not an image: ' + mimeType);
    photoCell.setValue('No Photo');
    return;
  }

  // 파일 크기 검증 (10MB)
  var fileSize = file.getSize();
  if (fileSize > CONFIG.MAX_FILE_SIZE) {
    writeLog_('PROCESS', String(row), 'SKIP',
      'File too large: ' + (fileSize / 1024 / 1024).toFixed(1) + 'MB');
    photoCell.setValue('No Photo');
    return;
  }

  // 공유 권한 설정 (IMAGE 함수 작동용 - 보기만 허용)
  try {
    file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  } catch (err) {
    writeLog_('PROCESS', String(row), 'WARN', 'Cannot set sharing: ' + err.message);
  }

  // Photo_Archive 폴더에 복사 정리
  archivePhoto_(file, sheet, row, cols);

  // IMAGE 함수 삽입
  var imageFormula = '=IMAGE("https://drive.google.com/uc?export=view&id=' + fileId + '", 1)';
  photoCell.setFormula(imageFormula);
  sheet.setRowHeight(row, CONFIG.ROW_HEIGHT);

  writeLog_('PROCESS', String(row), 'SUCCESS', 'Photo inserted: ' + fileId);
}


/**
 * 행 데이터에서 Drive URL 찾기
 * @param {Array} rowData
 * @param {number} skipIndex - photo 컬럼 인덱스(0-based, 이미 확인했으므로 건너뜀)
 * @returns {string|null}
 */
function findDriveUrl_(rowData, skipIndex) {
  for (var i = 0; i < rowData.length; i++) {
    var val = String(rowData[i] || '');
    if (val.match(/drive\.google\.com|docs\.google\.com/)) {
      return val;
    }
  }
  return null;
}


/**
 * Drive URL에서 파일 ID 추출
 * 지원 형식:
 *   https://drive.google.com/open?id=FILE_ID
 *   https://drive.google.com/file/d/FILE_ID/view
 *   https://docs.google.com/...FILE_ID...
 *   FILE_ID (순수 ID 문자열)
 * @param {string} url
 * @returns {string|null}
 */
function extractFileId_(url) {
  if (!url) return null;
  url = String(url).trim();

  // open?id=FILE_ID
  var match = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (match) return match[1];

  // /file/d/FILE_ID/ 또는 /d/FILE_ID/
  match = url.match(/\/(?:file\/)?d\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];

  // 순수 ID (URL이 아닌 경우)
  if (CONFIG.FILE_ID_PATTERN.test(url) && url.length > 10) {
    return url;
  }

  return null;
}


// ============================================
// 4. Photo_Archive 복사 정리
// ============================================

/**
 * 사진을 Photo_Archive 폴더에 {FullName}_{YYYYMMDD}.jpg로 복사
 * @param {File} file - Drive 파일 객체
 * @param {Sheet} sheet
 * @param {number} row
 * @param {Object} cols
 */
function archivePhoto_(file, sheet, row, cols) {
  try {
    var folder = getOrCreateFolder_(CONFIG.ARCHIVE_FOLDER);

    // 이름 가져오기
    var fullName = '';
    if (cols.name) {
      fullName = String(sheet.getRange(row, cols.name).getValue() || '').trim();
    }
    if (!fullName) {
      fullName = 'Unknown';
    }

    // 파일명 안전 처리 (특수문자 제거)
    fullName = fullName.replace(/[^a-zA-Z0-9가-힣\s_-]/g, '').replace(/\s+/g, '_');

    var dateStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd');
    var ext = getExtensionFromMime_(file.getMimeType());
    var archiveName = fullName + '_' + dateStr + ext;

    // 복사
    file.makeCopy(archiveName, folder);
    writeLog_('ARCHIVE', String(row), 'SUCCESS', 'Archived as: ' + archiveName);

  } catch (err) {
    writeLog_('ARCHIVE', String(row), 'WARN', 'Archive failed: ' + err.message);
    // 아카이브 실패해도 메인 처리는 계속
  }
}


/**
 * MIME 타입에서 확장자 반환
 * @param {string} mimeType
 * @returns {string}
 */
function getExtensionFromMime_(mimeType) {
  var map = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp',
    'image/svg+xml': '.svg'
  };
  return map[mimeType] || '.jpg';
}


/**
 * Drive 폴더 가져오기 (없으면 생성)
 * @param {string} folderName
 * @returns {Folder}
 */
function getOrCreateFolder_(folderName) {
  var folders = DriveApp.getFoldersByName(folderName);
  if (folders.hasNext()) {
    return folders.next();
  }
  return DriveApp.createFolder(folderName);
}


// ============================================
// 5. 컬럼 자동 감지
// ============================================

/**
 * 헤더 행에서 컬럼 위치 자동 감지
 * @param {Sheet} sheet
 * @returns {Object} {photo: number, email: number, name: number} (1-based)
 */
function detectColumns_(sheet) {
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var result = { photo: 3, email: 1, name: 2 }; // 폴백 기본값

  for (var i = 0; i < headers.length; i++) {
    var h = String(headers[i]).trim();

    if (CONFIG.HEADER_PHOTO.indexOf(h) !== -1) {
      result.photo = i + 1;
    }
    if (CONFIG.HEADER_EMAIL.indexOf(h) !== -1) {
      result.email = i + 1;
    }
    if (CONFIG.HEADER_NAME.indexOf(h) !== -1) {
      result.name = i + 1;
    }
  }

  return result;
}


// ============================================
// 6. backfillPhotos - 기존 행 일괄 처리
// ============================================

/**
 * 기존 행 중 Photo 컬럼이 비어있는 행을 일괄 처리
 * 실행 전 전체 대상 행 백업
 */
function backfillPhotos() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

    if (!sheet) {
      writeLog_('BACKFILL', '-', 'FAIL', 'Sheet "' + CONFIG.SHEET_NAME + '" not found');
      return;
    }

    ensureSheets_();
    var cols = detectColumns_(sheet);
    var lastRow = sheet.getLastRow();

    if (lastRow < 2) {
      writeLog_('BACKFILL', '-', 'SKIP', 'No data rows');
      return;
    }

    var processed = 0;
    var skipped = 0;
    var errors = 0;

    writeLog_('BACKFILL', '-', 'START', 'Processing rows 2 to ' + lastRow);

    for (var row = 2; row <= lastRow; row++) {
      try {
        var photoValue = sheet.getRange(row, cols.photo).getValue();

        // 이미 값이 있으면 스킵
        if (photoValue !== '' && photoValue !== null && photoValue !== undefined) {
          skipped++;
          continue;
        }

        // 백업 후 처리
        backupRow_(sheet, row);
        processPhotoForRow_(sheet, row, cols);
        processed++;

      } catch (err) {
        errors++;
        writeLog_('BACKFILL', String(row), 'ERROR', err.message);
      }
    }

    var summary = 'Done. Processed: ' + processed +
      ', Skipped: ' + skipped +
      ', Errors: ' + errors;
    writeLog_('BACKFILL', '-', 'COMPLETE', summary);

    SpreadsheetApp.getUi().alert('Backfill Complete\n\n' + summary);

  } catch (err) {
    writeLog_('BACKFILL', '-', 'ERROR', err.message + '\n' + err.stack);
  }
}


// ============================================
// 7. 백업 시스템
// ============================================

/**
 * 단일 행을 Backup 시트에 복사
 * @param {Sheet} sourceSheet
 * @param {number} row
 */
function backupRow_(sourceSheet, row) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var backupSheet = ensureSheet_(ss, CONFIG.BACKUP_SHEET,
      ['Timestamp', 'Original Row', 'Original Data...']);

    var lastCol = sourceSheet.getLastColumn();
    if (lastCol < 1) return;

    var rowData = sourceSheet.getRange(row, 1, 1, lastCol).getValues()[0];
    var timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(),
      'yyyy-MM-dd HH:mm:ss');

    var backupData = [timestamp, row].concat(rowData);
    backupSheet.appendRow(backupData);

  } catch (err) {
    writeLog_('BACKUP', String(row), 'WARN', 'Backup failed: ' + err.message);
  }
}


/**
 * 백업에서 복구
 * @param {number} rowNumber - 복구할 원본 행 번호
 */
function restoreFromBackup(rowNumber) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var backupSheet = ss.getSheetByName(CONFIG.BACKUP_SHEET);

    if (!backupSheet) {
      SpreadsheetApp.getUi().alert('Backup 시트가 없습니다.');
      return;
    }

    var sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
    if (!sheet) {
      SpreadsheetApp.getUi().alert('"' + CONFIG.SHEET_NAME + '" 시트가 없습니다.');
      return;
    }

    // 해당 행 번호의 가장 최근 백업 찾기
    var backupData = backupSheet.getDataRange().getValues();
    var latestBackup = null;

    for (var i = backupData.length - 1; i >= 1; i--) {
      if (Number(backupData[i][1]) === rowNumber) {
        latestBackup = backupData[i];
        break;
      }
    }

    if (!latestBackup) {
      SpreadsheetApp.getUi().alert('Row ' + rowNumber + '의 백업을 찾을 수 없습니다.');
      return;
    }

    // 원본 데이터 복원 (index 0=timestamp, 1=row, 2~=data)
    var originalData = latestBackup.slice(2);
    var targetRange = sheet.getRange(rowNumber, 1, 1, originalData.length);
    targetRange.setValues([originalData]);

    writeLog_('RESTORE', String(rowNumber), 'SUCCESS',
      'Restored from backup dated: ' + latestBackup[0]);
    SpreadsheetApp.getUi().alert('Row ' + rowNumber + ' 복구 완료.');

  } catch (err) {
    writeLog_('RESTORE', String(rowNumber), 'ERROR', err.message + '\n' + err.stack);
    SpreadsheetApp.getUi().alert('복구 실패: ' + err.message);
  }
}


// ============================================
// 8. 로그 시스템
// ============================================

/**
 * Log 시트에 기록
 * @param {string} action - 작업 유형
 * @param {string} targetRow - 대상 행
 * @param {string} result - 결과 (SUCCESS/FAIL/SKIP/ERROR/WARN)
 * @param {string} detail - 상세 내용
 */
function writeLog_(action, targetRow, result, detail) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ensureSheet_(ss, CONFIG.LOG_SHEET,
      ['Timestamp', 'Action', 'Row', 'Result', 'Detail']);

    var timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(),
      'yyyy-MM-dd HH:mm:ss');

    logSheet.appendRow([timestamp, action, targetRow, result, detail]);
  } catch (err) {
    // 로그 기록 자체가 실패하면 Logger로 폴백
    Logger.log('LOG_FAIL: ' + action + ' | ' + result + ' | ' + detail + ' | ' + err.message);
  }
}


/**
 * 30일 이상 된 로그 삭제
 * @param {number} days - 보존 일수 (기본 30)
 */
function cleanupOldLogs(days) {
  try {
    if (!days) days = CONFIG.LOG_RETENTION_DAYS;

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName(CONFIG.LOG_SHEET);
    if (!logSheet) return;

    var data = logSheet.getDataRange().getValues();
    var cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);

    var rowsToDelete = [];
    for (var i = data.length - 1; i >= 1; i--) {
      var logDate = new Date(data[i][0]);
      if (logDate < cutoff) {
        rowsToDelete.push(i + 1); // 1-based row
      }
    }

    // 아래에서부터 삭제 (인덱스 밀림 방지)
    for (var j = 0; j < rowsToDelete.length; j++) {
      logSheet.deleteRow(rowsToDelete[j]);
    }

    writeLog_('CLEANUP', '-', 'SUCCESS',
      'Deleted ' + rowsToDelete.length + ' logs older than ' + days + ' days');

  } catch (err) {
    writeLog_('CLEANUP', '-', 'ERROR', err.message);
  }
}


/**
 * 일일 처리 건수 요약
 * @returns {Object} {total, success, fail, skip, error}
 */
function getDailySummary() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName(CONFIG.LOG_SHEET);
    if (!logSheet) return { total: 0, success: 0, fail: 0, skip: 0, error: 0 };

    var data = logSheet.getDataRange().getValues();
    var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');

    var summary = { total: 0, success: 0, fail: 0, skip: 0, error: 0 };

    for (var i = 1; i < data.length; i++) {
      var logDate = Utilities.formatDate(new Date(data[i][0]),
        Session.getScriptTimeZone(), 'yyyy-MM-dd');
      if (logDate === today) {
        summary.total++;
        var result = String(data[i][3]).toUpperCase();
        if (result === 'SUCCESS') summary.success++;
        else if (result === 'FAIL' || result === 'REJECT') summary.fail++;
        else if (result === 'SKIP' || result === 'NO_PHOTO') summary.skip++;
        else if (result === 'ERROR') summary.error++;
      }
    }

    return summary;

  } catch (err) {
    return { total: 0, success: 0, fail: 0, skip: 0, error: 0, error_msg: err.message };
  }
}


// ============================================
// 9. 유틸리티
// ============================================

/**
 * Log/Backup 시트 자동 생성
 */
function ensureSheets_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureSheet_(ss, CONFIG.LOG_SHEET, ['Timestamp', 'Action', 'Row', 'Result', 'Detail']);
  ensureSheet_(ss, CONFIG.BACKUP_SHEET, ['Timestamp', 'Original Row', 'Original Data...']);
}


/**
 * 시트 존재 확인, 없으면 생성 + 헤더 삽입
 * @param {Spreadsheet} ss
 * @param {string} sheetName
 * @param {Array} headers
 * @returns {Sheet}
 */
function ensureSheet_(ss, sheetName, headers) {
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    if (headers && headers.length > 0) {
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    }
  }
  return sheet;
}
