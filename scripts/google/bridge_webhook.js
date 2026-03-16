/**
 * bridge_webhook.js — Google Apps Script
 * ========================================
 * Bridge 홈페이지로 Google Form 제출 데이터를 자동 전송합니다.
 *
 * 설치:
 * 1. Google Forms → 응답 Sheet → 확장 프로그램 → Apps Script
 * 2. 이 코드 전체 붙여넣기
 * 3. ScriptProperties에 다음 설정:
 *    - BRIDGE_API_URL: https://bridge-n7hk.onrender.com
 *    - BRIDGE_WEBHOOK_SECRET: (서버의 BRIDGE_WEBHOOK_SECRET과 동일)
 *    - FORM_TYPE: "job" 또는 "candidate"
 * 4. 트리거: onFormSubmit → 폼 제출 시
 *
 * 보안:
 * - HMAC-SHA256 서명으로 요청 인증
 * - PII는 서버에서 암호화 처리 (이쪽에서 절대 가공 금지)
 */

// ── 설정 ───────────────────────────────────────────────────────────────────────
var CONFIG = {
  API_URL:       PropertiesService.getScriptProperties().getProperty('BRIDGE_API_URL')    || 'https://bridge-n7hk.onrender.com',
  SECRET:        PropertiesService.getScriptProperties().getProperty('BRIDGE_WEBHOOK_SECRET') || '',
  FORM_TYPE:     PropertiesService.getScriptProperties().getProperty('FORM_TYPE')          || 'candidate',
  MAX_RETRIES:   2,
  TIMEOUT_MS:    10000,
};

// ── HMAC-SHA256 서명 생성 ───────────────────────────────────────────────────────
function _sign(body) {
  if (!CONFIG.SECRET) return '';
  var raw = Utilities.newBlob(body).getBytes();
  var key = Utilities.newBlob(CONFIG.SECRET).getBytes();
  var sig = Utilities.computeHmacSha256Signature(raw, key);
  return sig.map(function(b){ return ('0' + (b & 0xff).toString(16)).slice(-2); }).join('');
}

// ── 컬럼명 → DB 필드명 변환 (폼 헤더 → 서버 필드) ────────────────────────────
var _JOB_MAP = {
  'Timestamp':          'submitted_at',
  '학교명':             'school_name',
  'School Name':        'school_name',
  '지역':               'location',
  'Location':           'location',
  '교사 레벨':          'teaching_age',
  'Teaching Level':     'teaching_age',
  '근무시간':           'working_hours',
  'Working Hours':      'working_hours',
  '급여':               'salary_raw',
  'Salary':             'salary_raw',
  '시작일':             'start_date',
  'Start Date':         'start_date',
  '숙박':               'housing_type',
  'Housing':            'housing_type',
  '휴가':               'vacation',
  'Vacation':           'vacation',
  '복리후생':           'benefits',
  'Benefits':           'benefits',
  '담당자':             'contact_name',
  'Contact Name':       'contact_name',
  '연락처':             'phone',
  'Phone':              'phone',
  '이메일':             'email',
  'Email':              'email',
};

var _CAND_MAP = {
  'Timestamp':               'created_at',
  'Full Name':               'full_name',
  '이름':                    'full_name',
  'Email Address':           'email',
  '이메일':                  'email',
  'Phone Number':            'phone',
  '전화번호':                'phone',
  'Nationality':             'nationality',
  '국적':                    'nationality',
  'Teaching Level':          'teaching_age',
  '교사 레벨':               'teaching_age',
  'Visa Type':               'visa_type',
  '비자 종류':               'visa_type',
  'Available Start Date':    'start_date',
  '시작 가능일':             'start_date',
  'KakaoTalk ID':            'kakao_id',
  '카카오톡 ID':             'kakao_id',
};

function _mapFields(rowData, colMap) {
  var result = {};
  for (var key in rowData) {
    var dbKey = colMap[key] || key.toLowerCase().replace(/\s+/g, '_');
    var val = rowData[key];
    if (val !== null && val !== undefined && val !== '') {
      result[dbKey] = String(val);
    }
  }
  return result;
}

// ── 메인 트리거 함수 ───────────────────────────────────────────────────────────
function onFormSubmit(e) {
  try {
    var namedValues = e.namedValues; // { "컬럼명": ["값"] }
    var rowData = {};
    for (var col in namedValues) {
      rowData[col] = namedValues[col][0] || '';
    }

    var colMap = CONFIG.FORM_TYPE === 'job' ? _JOB_MAP : _CAND_MAP;
    var mapped = _mapFields(rowData, colMap);

    var payload = JSON.stringify({ type: CONFIG.FORM_TYPE, data: mapped });
    var sig = _sign(payload);

    var options = {
      method: 'post',
      contentType: 'application/json',
      payload: payload,
      headers: { 'x-bridge-signature': sig },
      muteHttpExceptions: true,
      followRedirects: true,
    };

    var url = CONFIG.API_URL + '/api/admin/sync/incoming';
    var retries = 0;
    var resp = null;

    while (retries <= CONFIG.MAX_RETRIES) {
      try {
        resp = UrlFetchApp.fetch(url, options);
        var code = resp.getResponseCode();
        if (code === 200 || code === 201) {
          Logger.log('[Bridge Webhook] 전송 성공: ' + resp.getContentText().slice(0, 200));
          return;
        }
        Logger.log('[Bridge Webhook] HTTP ' + code + ' — 재시도 ' + retries);
      } catch (fetchErr) {
        Logger.log('[Bridge Webhook] 네트워크 오류: ' + fetchErr);
      }
      retries++;
      if (retries <= CONFIG.MAX_RETRIES) Utilities.sleep(2000 * retries);
    }

    // 최종 실패: 관리자 이메일 알림
    var adminEmail = Session.getActiveUser().getEmail() || 'bridgejobkr@gmail.com';
    GmailApp.sendEmail(
      adminEmail,
      '[Bridge Webhook] 전송 실패 알림',
      'Form 제출 데이터가 Bridge 서버로 전송되지 못했습니다.\n\n' +
      'Type: ' + CONFIG.FORM_TYPE + '\n' +
      '응답 코드: ' + (resp ? resp.getResponseCode() : 'N/A') + '\n\n' +
      '수동으로 어드민에서 직접 입력해주세요.'
    );

  } catch (err) {
    Logger.log('[Bridge Webhook] 처리 오류: ' + err);
  }
}

// ── 테스트 함수 (수동 실행용) ──────────────────────────────────────────────────
function testWebhook() {
  var testData = CONFIG.FORM_TYPE === 'job'
    ? { school_name: 'Test School', location: 'Seoul', teaching_age: 'Elementary' }
    : { full_name: 'Test Teacher', nationality: 'USA', teaching_age: 'Middle' };

  var payload = JSON.stringify({ type: CONFIG.FORM_TYPE, data: testData });
  var sig = _sign(payload);

  var resp = UrlFetchApp.fetch(CONFIG.API_URL + '/api/admin/sync/incoming', {
    method: 'post',
    contentType: 'application/json',
    payload: payload,
    headers: { 'x-bridge-signature': sig },
    muteHttpExceptions: true,
  });

  Logger.log('[Test] ' + resp.getResponseCode() + ': ' + resp.getContentText().slice(0, 300));
}
