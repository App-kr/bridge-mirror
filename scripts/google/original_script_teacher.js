//=========================================================
// ---------------------- 1. 환경 설정 및 상수 정의 ----------------------
//=========================================================

const sourceSpreadsheetId = '1PveCb7yfPhsmV-YwERf2PjoaKtXJmB0uJngu1dhTxM';  // 구글시트 아이디
const destinationFolderId = '1S-bqyye-r8kIPFlbrrjKiAmtFZn7IP9uabezxu-S0bU4liANAPFwIsM41';   // 구글드라이브 폴더 (ID는 예시)
const sh_name_form = 'Form'; // Google Form에 신청자가 제출한 내용을 저장하는 데이터 시트명
const sh_name_wait = 'New'; // 새로 제출된 값을 저장, 관리하는 시트명
const ADMIN_EMAIL = "bridgejobkr@gmail.com"; // 관리자 이메일 주소

// PDF 관련 설정
let fileNameFormat = '{FullName}_Application_{datetime}';
const sendAsPDF = 0; // PDF 없이 이메일만 보내기 위해 0으로 설정


//=========================================================
// ---------------------- 3. 오류 및 제한 처리 함수 ----------------------
//=========================================================
var errorLog = []; // 오류 로그를 저장하는 배열
var errorCount = 0; // 오류 횟수

// 오류 로그를 모아서 발송하는 함수
function sendErrorLogEmail(errorDetails, errorCode, errorFunction, errorMessage, trigger) {
  var emailSubject = "BRIDGE원어민 신청서_수정금지" + " 메일발송량 경고";
  var emailBody =     '<p><strong>경고 파일 이름: BRIDGE원어민 신청서_수정금지</strong></p>'
    + '<p><strong>경고 사유:</strong> 메일 발송량 초과</p>'
    + `<p><strong>에러 코드:</strong> ${errorCode}</p>`
    + `<p><strong>에러 함수:</strong> ${errorFunction}</p>`
    + `<p><strong>에러 메시지:</strong> ${errorMessage}</p>`
    + `<p><strong>트리거:</strong> ${trigger}</p>`
    + '<br>'
    + '<p><strong>Warning File Name:</strong> BRIDGE원어민 신청서_수정금지</p>'
    + '<p><strong>Reason for Warning:</strong> Exceeded email sending limit</p>'
    + `<p><strong>Error Code:</strong> ${errorCode}</p>`
    + `<p><strong>Error Function:</strong> ${errorFunction}</p>`
    + `<p><strong>Error Message:</strong> ${errorMessage}</p>`
    + `<p><strong>Trigger:</strong> ${trigger}</p>`;
  ;  
  // 경고 메일 발송
  GmailApp.sendEmail(
    ADMIN_EMAIL,
    emailSubject,
    '', // 텍스트 내용은 생략하고 HTML로만 보냄
    { htmlBody: emailBody }
  );
  
  Logger.log("경고 메일 발송 완료: " + emailSubject);
}

// 오류 로그를 모아서 5회당 한 번 이메일로 발송하는 함수
function sendErrorLogEmail() {
  if (errorLog.length > 0 && errorCount % 5 === 0) {
    var errorDetails = errorLog.join("\n\n"); // 로그를 모두 합침
    GmailApp.sendEmail(ADMIN_EMAIL, "5회 오류 발생 - 오류 로그", errorDetails);
    
    Logger.log("오류 로그 이메일 발송 완료.");
    
    // 로그 배열과 오류 카운트를 초기화
    errorLog = [];
  }
}

// 관리자 이메일 발송량 체크 및 발송 함수 (기존 코드의 로직을 유지)
function sendAdminEmailWithLimitCheck(sourceData) {
  var scriptProperties = PropertiesService.getScriptProperties();

  // 발송 횟수 확인
  var emailCount = parseInt(scriptProperties.getProperty('dailyEmailCount')) || 0;
  var lastSentDate = scriptProperties.getProperty('lastSentDate') || '';

  // 오늘 날짜 가져오기
  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');

  // 날짜가 바뀌었으면 발송 횟수 초기화
  if (today !== lastSentDate) {
    emailCount = 0;
    scriptProperties.setProperty('lastSentDate', today);
  }

  // 발송 횟수 체크 (60회 초과 시 경고 메일 전송)
  if (emailCount >= 60) {
    sendErrorLogEmail("Exceeded email sending limit", "60 emails limit reached", "sendAdminEmailWithLimitCheck", "Exceeded daily email limit", "Email sending trigger");
    Logger.log("경고: 1일 이메일 발송량이 60회를 초과했습니다.");
  }

  // 이메일 발송 (기존 발송 계속 진행)
  const fullName = sourceData[4]; 
  
  try {
    // 발송 횟수 증가 및 저장
    emailCount += 1;
    scriptProperties.setProperty('dailyEmailCount', emailCount);

    Logger.log(`현재 이메일 발송 횟수: ${emailCount}`);
  } catch (e) {
    // 오류 발생 시 로그 추가
    errorLog.push(`오류 발생 시간: ${new Date()}\n오류 메시지: ${e.message}\n`);
    errorCount++;

    Logger.log("Email sending failed: " + e.message);
    sendErrorLogEmail(e.message, "sendAdminEmailWithLimitCheck", e.message, "Email sending trigger");
  }
}

// 발송 횟수를 초기화하는 함수
function resetDailyEmailCount() {
  PropertiesService.getScriptProperties().deleteProperty('dailyEmailCount');
  Logger.log("이메일 발송 횟수가 초기화되었습니다.");
}

//=========================================================
// ---------------------- 4. 메인 트리거 함수 (onFormSubmit) ----------------------
//=========================================================
/////// 구글 Form 제출 시 실행되는 트리거 함수입니다.
function onFormSubmit(e) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet();
    const sourceSheet = sheet.getSheetByName(sh_name_form);
    const targetSheet = sheet.getSheetByName(sh_name_wait);

    // 'Form' 시트에서 마지막 행의 데이터를 가져옵니다.
    const lastRow = sourceSheet.getLastRow();
    const allData = sourceSheet.getRange(lastRow, 1, 1, sourceSheet.getLastColumn()).getValues();
    const sourceData = allData.length > 0 ? allData[0] : undefined; 

    // 데이터 유효성 검사 및 종료
    if (!sourceData || sourceData.length === 0 || sourceData.every(item => item === '')) {
      Logger.log("onFormSubmit - sourceData가 비어 있습니다. 조용히 종료합니다.");
      return; 
    }

    Logger.log("onFormSubmit - sourceData 값: " + JSON.stringify(sourceData));

    // 제출자 이메일로 안내 메일 발송
    sendApplicantEmail(sourceData);

    // 관리자에게 이메일 발송 
    sendAdminEmail(sourceData);  

    // New 시트에 데이터를 옮김
    insertIntoWaitSheet(sourceData, targetSheet);

    // ★ 사진 자동 삽입 (New 시트 마지막 행)
    processNewRowPhoto(sourceData, targetSheet);

  } catch (error) {
    Logger.log("Error in onFormSubmit: " + error.message);
    GmailApp.sendEmail(ADMIN_EMAIL, "오류 발생 알림", error.message);
  }
}






//=========================================================
// ---------------------- 5. 제출자 안내 이메일 발송 (sendApplicantEmail) ----------------------
//=========================================================

function sendApplicantEmail(data) {
  const applicantEmail = data[1]; // 이메일 주소
  const applicantName = data[4];  // Full name

  const subject = `${applicantName}, your application has been received successfully!`;

// ⭐ V53 수정: 블랙 텍스트 적용 및 파란 박스 내용(사후 안내/해외지원자) 교체
const htmlBody = `
<html>
<body style="color: #000000; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 15px; line-height: 1.7;">
  <div style="max-width: 600px;">
    
    <p>Dear ${applicantName},</p>

    <p>Thank you for reaching out to us! We have received your application. It is a pleasure to have the opportunity to review your profile for BRIDGE Agency.</p>

    <p>Our team is now carefully reviewing your documents. <strong>If you find that any files (CV, photos, or intro video) were missed in the initial form, feel free to reply to this email and attach them whenever you're ready.</strong></p>

    <p>Once everything is set, we will send a Google Meet invitation based on your availability.</p>

    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #1a73e8; margin: 20px 0;">
      <p style="margin: 0; font-weight: bold;">A thoughtful request:</p>
      <p style="margin: 5px 0 10px 0;">We truly value your time as much as our own. If you happen to find another position or your plans change during the process, please let us know with a quick reply.</p>
      <hr style="border: 0; border-top: 1px solid #1a73e8; margin: 10px 0;">
      <p style="margin: 0; font-weight: bold;">For Overseas Applicants:</p>
      <p style="margin: 5px 0 0 0;">Please reach out to us again once your documents are fully prepared to confirm your readiness for the next steps.</p>
    </div>

    <p>We kindly ask you to keep an eye on your notifications so we can connect at the scheduled time.</p>

    <p>Thank you for being part of the BRIDGE community. We look forward to our conversation!</p>

    <br>
    <p>Warm regards,</p>
    <p>BRIDGE Team<br>
    <a href="mailto:bridgejobkr@gmail.com" style="color: #1a73e8; text-decoration: none;">bridgejobkr@gmail.com</a></p>

  </div>
</body>
</html>
`;
  GmailApp.sendEmail(applicantEmail, subject, '', {
    htmlBody: htmlBody,
    name: "The BRIDGE Team",
    from: "bridgejobkr@gmail.com"
  });
}




//=========================================================
// ---------------------- 6. 관리자 이메일 발송 및 본문 생성 (sendAdminEmail) ----------------------
//=========================================================

function sendAdminEmail(data) {
  const adminEmail = ADMIN_EMAIL;
  
  // 날짜 데이터 포맷팅
  const dateOfBirth = new Date(data[7]); // Date of Birth (Form Index 7)
  const startDate = new Date(data[18]); // Start date (Form Index 18)

  // 1. 날짜 깨짐 및 년도/월 포맷팅
  let birthYearTwoDigits = '';
  let startMonthTwoDigits = '';
  
  if (!isNaN(dateOfBirth.getTime()) && dateOfBirth.getFullYear() > 1970) {
      birthYearTwoDigits = Utilities.formatDate(dateOfBirth, 'Asia/Seoul', 'yy');
  } else {
      birthYearTwoDigits = 'XX'; // 데이터가 유효하지 않으면 XX로 표시
  }

  if (!isNaN(startDate.getTime()) && startDate.getFullYear() > 1970) {
      startMonthTwoDigits = Utilities.formatDate(startDate, 'Asia/Seoul', 'MM');
  } else {
      startMonthTwoDigits = 'XX'; // 데이터가 유효하지 않으면 XX로 표시
  }

  // 3. 주요 데이터 한국어 번역
  const translatedNationality = translateToKoreanDynamically(data[5]);  // 국적
  const translatedCurrentLocation = translateToKoreanDynamically(data[9]); // 현위치 (V30 수정: 제목에 한글 변환 적용)
  const translatedGender = translateToKoreanDynamically(data[8]); // 성별
  const translatedTarget = translateToKoreanDynamically(data[19]); // 타겟(희망연령)
  const translatedEmployment = translateToKoreanDynamically(data[23]); // 고용상태
  const currentSalary = data[25] || 'N/A'; // 현급여
  const desiredSalary = data[26] || 'N/A'; // 희망급여

  // 2. 관리자 이메일 제목 생성 (국적/출생2자리/현위치(한글)/시작일00월 원어민 구직신청접수)
  const subject = `${translatedNationality}/${birthYearTwoDigits}년생/${translatedCurrentLocation}/${startMonthTwoDigits}월 원어민 구직신청접수`;

  // ⭐️ V30 핵심 수정: 요약 박스 내용 및 폰트 크기 변경 ⭐️
  const htmlBody = `
    <html>
    <head>
      <style>
        body { 
          font-family: Arial, sans-serif; 
          margin: 0; 
          padding: 0; 
          background-color: #f4f4f4; 
        }
        .container { 
          max-width: 650px; 
          margin: 20px auto; 
          background-color: #ffffff; 
          border: 1px solid #ddd; 
          border-radius: 8px; 
          overflow: hidden; 
          box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }
        .header { background-color: #007bff; color: white; padding: 18px; text-align: center; font-size: 20px; font-weight: bold; }
        .content { padding: 25px; }
        .data-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .data-table td { 
          padding: 12px; 
          border-bottom: 1px solid #eee; 
          font-size: 15px; 
          color: #000000; 
          word-break: break-word; 
        }
        .label { 
          background-color: #f9f9f9; 
          font-weight: bold; 
          color: #000000; 
          width: 30%; 
        }
        .highlight-box {
          border: 2px solid #ffcc00; 
          padding: 15px; 
          margin-bottom: 25px;
          background-color: #fffde7; 
          border-radius: 6px;
          text-align: center;
          font-weight: bold;
          font-size: 19px; /* 요약 박스 폰트 크기 키움 */
          line-height: 1.5; /* 줄 간격 추가 */
          color: #000000;
        }
        .email-link { color: #007bff; text-decoration: none; font-weight: bold; }
        
        /* 모바일 반응형 */
        @media only screen and (max-width: 650px) {
            .container { margin: 10px; }
            .data-table td { display: block; width: 100%; box-sizing: border-box; }
            .label { background-color: #f0f0f0; }
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">새 원어민 구직 신청서가 접수되었습니다</div>
        <div class="content">
          
          <div class="highlight-box">
            ${translatedNationality} / ${translatedGender} / ${translatedTarget} / ${translatedEmployment}
            <br>
            현급여: ${currentSalary} / 희망급여: ${desiredSalary}
          </div>

          <p><a href="mailto:${data[1]}" class="email-link">${data[1]}</a></p>

          <table class="data-table">
            <tr><td class="label">이름</td><td>${data[4]}</td></tr>
            <tr><td class="label">국적</td><td>${translatedNationality}</td></tr>
            <tr><td class="label">배경</td><td>${translateToKoreanDynamically(data[6])}</td></tr>
            <tr><td class="label">현위치</td><td>${translatedCurrentLocation}</td></tr>
            <tr><td class="label">시작일</td><td>${Utilities.formatDate(new Date(data[18]), 'Asia/Seoul', 'yy.MM.dd')}</td></tr>
            <tr><td class="label">희망지역</td><td>${translateToKoreanDynamically(data[20])}</td></tr>
            <tr><td class="label">희망급여</td><td>${desiredSalary}</td></tr>
            <tr><td class="label">서류상태</td><td>${translateToKoreanDynamically(data[17])}</td></tr>
            <tr><td class="label">ARC/비자만료</td><td>${data[13]}</td></tr>
            <tr><td class="label">고용상태</td><td>${translatedEmployment}</td></tr>
            <tr><td class="label">건강</td><td>${translateToKoreanDynamically(data[30])}</td></tr>
            <tr><td class="label">카톡ID</td><td>${data[33]}</td></tr>
            <tr><td class="label">모바일</td><td>${data[34]}</td></tr>
            <tr><td class="label">참조</td><td>${translateToKoreanDynamically(data[24])}</td></tr>
          </table>

          <div class="section-title" style="font-size: 16px; font-weight: bold; color: #007bff; margin-top: 25px; margin-bottom: 12px;">첨부 파일 및 시트 링크</div>
          <p style="font-size: 15px; color: #000000;">
            첨부 파일 링크: <a href="${data[3]}" target="_blank" class="email-link">파일 확인</a><br>
            <span style="font-size:12px; color:#999;">(링크는 Google Drive 정책에 따라 접근 권한이 필요할 수 있습니다)</span>
          </p>

          <p style="text-align:center; font-size: 13px; color: #666; margin-top: 30px;">
            상세 내용은 원어민 자료 파일 및 New 시트를 참고하십시오.
          </p>

        </div>
      </div>
    </body>
    </html>
  `;
  
  // 이메일 발송
  try {
    MailApp.sendEmail({
      to: adminEmail,
      subject: subject,
      htmlBody: htmlBody
    });
  } catch (e) {
    Logger.log(`Error sending admin email: ${e.toString()}`);
  }
}




//=========================================================
// ---------------------- 7. PDF 관련 함수 (현재 미사용) ----------------------
//=========================================================
// PDF 저장 함수 - 매핑이 오류가 발생되어 지금은 사용을 잠시 중단합니다. 
function SaveAsPDF(spreadsheetId, sheetName, printRange, folderId, pdfFileName) {
  // 현재 이 함수 내부에는 주석 외에 다른 코드가 없습니다.
}

// PDF 생성 함수입니다. 
function createPDF(sourceData) {
  // 현재 이 함수 내부에는 주석 외에 다른 코드가 없습니다.
}

// PDF 저장 함수 (중복 정의 – 원본 유지)
function SaveAsPDF(sheetId, sheetName, printRange, folderId, pdfFileName) {
  const folder = DriveApp.getFolderById(folderId);
  const spreadsheet = SpreadsheetApp.openById(sheetId);
  const sheet = spreadsheet.getSheetByName(sheetName);

  const url = spreadsheet.getUrl().replace(/edit$/, '') 
            + 'export?exportFormat=pdf&format=pdf'
            + '&gid=' + sheet.getSheetId()
            + '&range=' + printRange 
            + '&size=A4'
            + '&portrait=true'
            + '&scale=4'
            + '&sheetnames=false&printtitle=false&pagenumbers=false'
            + '&gridlines=false'
            + '&fzr=false';

  const token = ScriptApp.getOAuthToken();
  const response = UrlFetchApp.fetch(url, {
    headers: {
      'Authorization': 'Bearer ' + token
    }
  });

  const pdfBlob = response.getBlob().setName(pdfFileName);
  const pdfFile = folder.createFile(pdfBlob);

  return pdfFile.getId();
}

// 설문지 데이터를 기반으로 문서를 생성하는 함수입니다.
function sendEmailfromForm() {
  // 현재 이 함수 내부에는 주석 외에 다른 코드가 없습니다.
}

// 헤더와 값을 딕셔너리로 변환하는 함수
function parseFormData(values, header) {
  // 현재 이 함수 내부에는 주석 외에 다른 코드가 없습니다.
}



//=========================================================
// ----------------------  Form (Source) 및 New (Target) 헤더 정의 ----------------------
// (주: Form 헤더는 0-based index, New 시트 매핑은 1-based index)
//=========================================================

/*
// Form Source Headers (37 columns, 0-based index)
[0] 타임스탬프
[1] 이메일 주소
[2] How to
[3] Attach your files 
[4] Full name
[5] Nationality
[6] Family Ancestry Background 
[7] Date of Birth
[8] Gender
[9] Current Location
[10] Educational Background (Degree)
[11] Major
[12] Certification
[13] E visa
[14] ARC holders
[15] Passport
[16] Criminal Record (해외)
[17] Document Status 
[18] Start date
[19] Target
[20] Area prefs
[21] Job prefs (Notes)
[22] Experience
[23] Employment
[24] Reference
[25] Current salary
[26] Desired salary
[27] Housing
[28] Personal Considerations (Situation)
[29] Religion 
[30] Health Information 
[31] Criminal Record Check (한국)
[32] Interview time
[33] KakaoTalk
[34] Mobile Phone
[35] Agreement
[36] Facts
*/

/*
// New Target Headers (45 columns, 1-based index) - ARC holders(Form[14])를 5번으로 이동
1. 이메일 주소 (Form[1])
2. Full name (Form[4])
3. Photo (Placeholder)
4. No (Placeholder)
5. ARC holders (Form[14])  <-- AN열에서 이동 삽입
6. Nationality (Form[5])
7. Family Ancestry Background (Form[6])
8. Date of Birth (Form[7], 년도 2자리)
9. Gender (Form[8])
10. Current Location (Form[9])
11. Start date (Form[18])
12. Target (Form[19])
13. Area prefs (Form[20])
14. Reference (Form[24])
15. Experience (Form[22])
16. Employment (Form[23])
17. Job prefs (Form[21])
18. Interview (Placeholder)
19. Apply (Placeholder)
20. Current salary (Form[25])
21. Desired salary (Form[26])
22. Degree (Form[10])
23. Major (Form[11])
24. Certification (Form[12])
25. Documents (Form[17])
26. Health Information (Form[30])
27. Situation (Form[28])
28. Pet (Placeholder)
29. Tattoos (Placeholder)
30. Piercings (Placeholder)
31. Marital (Placeholder)
32. Housing (Form[27])
33. Religion (Form[29])
34. E visa (Form[13])
35. Interview time (Form[32])
36. KakaoTalk (Form[33])
37. Mobile Phone (Form[34])
38. Criminal Record (Form[16] 해외)
39. Criminal Record in Korea (Form[31] 한국)
40. Passport (Form[15])
41. Agreement (Form[35])
42. Facts (Form[36])
43. How to (Form[2])
44. 타임스탬프 (Form[0])
*/


function insertIntoWaitSheet(sourceData, targetSheet, currentNo) {
  const lastRow = targetSheet.getLastRow() + 1;

  const NEW_TO_FORM_MAP = {
    1: 1,   // A: 이메일 주소
    2: 4,   // B: Full name
    5: 14,  // E: ARC holders
    6: 5,   // F: Nationality
    7: 6,   // G: Family Ancestry Background
    8: 7,   // H: Date of Birth
    9: 8,   // I: Gender
    10: 9,  // J: Current Location
    11: 18, // K: Start date
    12: 19, // L: Target
    13: 20, // M: Area prefs
    14: 24, // N: Reference
    15: 22, // O: Experience
    16: 23, // P: Employment
    17: 21, // Q: Job prefs (Notes)
    20: 25, // T: Current salary
    21: 26, // U: Desired salary
    22: 34, // V: Interview time
    23: 10, // W: Degree
    24: 11, // X: Major
    25: 12, // Y: Certification
    26: 17, // Z: Documents
    27: 32, // AA: Health Information
    28: 30, // AB: Personal Considerations
    30: 28, // AD: Dependents Pets
    31: 27, // AE: Marital Status
    32: 29, // AF: Housing
    33: 31, // AG: Religion
    34: 13, // AH: E visa
    35: 35, // AI: KakaoTalk
    36: 36, // AJ: Mobile Phone
    37: 16, // AK: Criminal Record (해외)
    38: 33, // AL: Criminal Record in Korea
    39: 37, // AM: Agreement
    40: 38, // AN: Facts
    41: 2,  // AO: How to
    42: 0,  // AP: 타임스탬프
    49: 39  // 메모
  };

  const MAX_TARGET_COL = 49;
  const locationKeys = new Set(["서울", "경기", "인천", "대전", "대구", "부산", "울산", "광주", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]);

  const rawMajor   = String(sourceData[10] || '').toLowerCase();
  const rawCertRaw = String(sourceData[12] || '').toLowerCase();

  const BOLD_MAJOR_KEYWORDS = [
    'education', 'teaching', 'english', 'tesol', 'tefl', 'celta', 'delta',
    'linguistics', 'english literature', 'pgce'
  ];
  const BOLD_CERT_KEYWORDS = [
    'teaching license', 'teaching certificate', 'pgce', 'delta', 'celta',
    'tesol', 'tefl'
  ];

  const isBoldRow =
    BOLD_MAJOR_KEYWORDS.some(k => rawMajor.includes(k)) ||
    BOLD_CERT_KEYWORDS.some(k => rawCertRaw.includes(k));

  for (let targetCol = 1; targetCol <= MAX_TARGET_COL; targetCol++) {
    let value = '';
    const srcIndex = NEW_TO_FORM_MAP[targetCol];

    if ([3, 4, 18, 19, 44, 45, 46, 47, 48].includes(targetCol)) {
      if (targetCol === 3)      value = 'Photo';
      else if (targetCol === 4) value = currentNo;
      else                      value = '';
    }
    else if (srcIndex !== undefined && srcIndex < sourceData.length) {
      let raw = sourceData[srcIndex];
      let cleanRaw = (raw !== null && raw !== undefined && typeof raw === 'string')
        ? raw.replace(/,/g, '').trim()
        : raw;

      if ([1, 14, 20, 21, 22, 35, 36].includes(targetCol)) {
        // 번역 없이 원문 그대로
        value = cleanRaw;
      }
      else if (targetCol === 8) {
        // Date of Birth → 년도 2자리
        const d = new Date(raw);
        value = (!isNaN(d.getTime())) ? d.getFullYear().toString().slice(-2) : raw;
      }
      else if ([11, 43].includes(targetCol)) {
        // Start date, 기타 날짜 → yy.MM.dd
        const d = new Date(raw);
        value = (!isNaN(d.getTime()))
          ? Utilities.formatDate(d, 'Asia/Seoul', 'yy.MM.dd')
          : raw;
      }
      else if (targetCol === 42) {
        // ★ 타임스탬프 → 번역 함수 진입 차단, 풀 날짜시간 포맷
        const d = new Date(raw);
        value = (!isNaN(d.getTime()))
          ? Utilities.formatDate(d, 'Asia/Seoul', 'yyyy.MM.dd HH:mm')
          : String(raw);
      }
      else {
        value = translateToKoreanDynamically(cleanRaw);
        if (typeof value === 'string') value = value.replace(/,/g, '');
      }
    }

    const cell = targetSheet.getRange(lastRow, targetCol);
    cell.setValue(value).setFontColor("black").setFontWeight("normal");

    // 기존 볼드 규칙
    if ([4, 6, 10, 11, 12, 13, 16, 21, 32].includes(targetCol)) {
      cell.setFontWeight("bold");
    }

    // 빨간 경고 키워드
    const s = String(value);
    if (["절대모름", "곧알림", "반려동물", "강아지", "고양이", "애기있음"].some(k => s.includes(k))) {
      cell.setFontColor("red").setFontWeight("bold");
    }

    // 현위치 파란 볼드
    if (targetCol === 10 && value && locationKeys.has(s.trim())) {
      cell.setFontColor("blue").setFontWeight("bold");
    }

    // 교육/티칭/영어/PGCE 컬럼 볼드 (W,X,Y)
    if (isBoldRow && [23, 24, 25].includes(targetCol)) {
      cell.setFontWeight("bold");
    }
  }
}




//=========================================================
// 9. 번역 및 콤마 완전 제거 로직 (Final Master - Integrity Patch)
// N(Reference), U(Salary) 등에서 'IT' 오인식 발생을 원천 차단함
//=========================================================
function translateToKoreanDynamically(rawValue) {
  if (rawValue === undefined || rawValue === null || rawValue === '') return rawValue;
  let str = String(rawValue).trim();

  if (str.includes('@') || str.toLowerCase().includes('anytime')) return str;

  const values = str.split(',').map(v => v.trim());
  const translatedValues = [];

  for (const value of values) {
    if (value === '') continue;
    let translated = value;
    const v = value.toLowerCase();

    // =====================================================
    // [★ 최우선] "Bachelor of Arts/Science in [전공]" 파싱
    // =====================================================
    const bachelorMatch = v.match(/bachelor(?:'s)?\s+of\s+(?:arts?|science|applied science|education|fine arts?|business|commerce|laws?|music|nursing|social work)?\s*(?:in|with)?\s*(.+)/);
    if (bachelorMatch) {
      const actualMajor = bachelorMatch[1].trim();
      if (actualMajor.length > 1) {
        translated = translateToKoreanDynamically(actualMajor);
      } else {
        if (v.includes('fine arts'))                          translated = '순수미술';
        else if (v.includes('education'))                    translated = '교육학';
        else if (v.includes('music'))                        translated = '음악';
        else if (v.includes('nursing'))                      translated = '간호학';
        else if (v.includes('social work'))                  translated = '사회복지';
        else if (v.includes('business') || v.includes('commerce')) translated = '경영학';
        else if (v.includes('laws'))                         translated = '법학';
        else                                                  translated = '학사';
      }
      translatedValues.push(translated);
      continue;
    }

    // [FIX 1] Target (희망연령)
    if      (v.includes('pre-k') || v.includes('kindergarten')) { translated = '유'; }
    else if (v.includes('elementary'))                           { translated = '초'; }
    else if (v.includes('middle school'))                        { translated = '중'; }
    else if (v.includes('high school'))                          { translated = '고'; }
    else if (v === 'adults' || v.includes('adult'))              { translated = '성'; }
    else if (v === 'no preferences' || v === 'no preference')    { translated = '무관'; }

    // [FIX 2] Area prefs
    else if (v.includes('metropol'))    { translated = '수도'; }
    else if (v.includes('medium size')) { translated = '중도'; }
    else if (v.includes('small city'))  { translated = '소도'; }

    // [FIX 3] Certification
    else if (v.includes('teaching license') || v.includes('teaching certificate')) { translated = '교사'; }
    else if (v.includes('pgce'))            { translated = 'PGCE'; }
    else if (v.includes('delta'))           { translated = '델타'; }
    else if (v.includes('celta'))           { translated = '셀타'; }
    else if (v.includes('tesol'))           { translated = '테솔'; }
    else if (v.includes('tefl'))            { translated = '테플'; }
    else if (v.includes('on the process'))  { translated = '진행중'; }
    else if (v.includes('no certification')){ translated = '자격증X'; }

    // 한국 광역시/도
    else if (v.includes('seoul'))    { translated = '서울'; }
    else if (v.includes('busan') || v.includes('pusan')) { translated = '부산'; }
    else if (v.includes('incheon'))  { translated = '인천'; }
    else if (v.includes('daegu'))    { translated = '대구'; }
    else if (v.includes('daejeon'))  { translated = '대전'; }
    else if (v.includes('gwangju'))  { translated = '광주'; }
    else if (v.includes('ulsan'))    { translated = '울산'; }
    else if (v.includes('sejong'))   { translated = '세종'; }
    else if (v.includes('gyeonggi')){ translated = '경기'; }
    else if (v.includes('gangwon'))  { translated = '강원'; }
    else if (v.includes('chungbuk')){ translated = '충북'; }
    else if (v.includes('chungnam')){ translated = '충남'; }
    else if (v.includes('jeonbuk')) { translated = '전북'; }
    else if (v.includes('jeonnam')) { translated = '전남'; }
    else if (v.includes('gyeongbuk')){ translated = '경북'; }
    else if (v.includes('gyeongnam')){ translated = '경남'; }
    else if (v.includes('jeju'))     { translated = '제주'; }

    // 주요 도시
    else if (v.includes('suwon'))    { translated = '수원'; }
    else if (v.includes('yongin'))   { translated = '용인'; }
    else if (v.includes('goyang') || v.includes('ilsan'))     { translated = '고양/일산'; }
    else if (v.includes('seongnam') || v.includes('bundang')) { translated = '성남/분당'; }
    else if (v.includes('hanam'))    { translated = '하남'; }
    else if (v.includes('hwaseong') || v.includes('dongtan')) { translated = '화성/동탄'; }
    else if (v.includes('cheonan')) { translated = '천안'; }
    else if (v.includes('cheongju')){ translated = '청주'; }
    else if (v.includes('jeonju'))  { translated = '전주'; }
    else if (v.includes('pohang'))  { translated = '포항'; }
    else if (v.includes('changwon')){ translated = '창원'; }
    else if (v.includes('geoje'))   { translated = '거제'; }
    else if (v.includes('yangsan')) { translated = '양산'; }
    else if (v.includes('songdo'))  { translated = '송도'; }
    else if (v.includes('myeongji')){ translated = '명지'; }

    // 학위 단계
    else if (v.includes("bachelor's degree from one of the 7 eligible countries")) { translated = '정상'; }
    else if (v.includes("i have a bachelor's or higher from korea"))               { translated = '한국학위'; }
    else if (v.includes("graduated, but diploma not available"))                    { translated = '학위아직x'; }
    else if (v.includes("bachelor's degree (other country)"))                       { translated = '타국가학위'; }
    else if (v === 'master')                    { translated = '석사'; }
    else if (v === 'doctor' || v.includes('ph.d')) { translated = '박사'; }
    else if (v === 'associate')                 { translated = '전문대'; }
    else if (v.includes('online degree'))       { translated = '온라인'; }
    else if (v.includes('did not graduate'))    { translated = '졸업X'; }

    // 전공: 교육계열 (세부→broad 순서 엄수)
    else if (v.includes('early childhood education') || v.includes('ece')) { translated = '유아교육'; }
    else if (v.includes('elementary education') || v.includes('primary education') || v.includes('intermediate phase')) { translated = '초등교육'; }
    else if (v.includes('secondary education')) { translated = '중등교육'; }
    else if (v.includes('physical education') || v.includes('p.e.')) { translated = '체육교육'; }
    else if (v.includes('special education'))   { translated = '특수교육'; }
    else if (v.includes('english education'))   { translated = '영어교육'; }
    else if (v.includes('music education'))     { translated = '음악교육'; }
    else if (v.includes('art education'))       { translated = '미술교육'; }
    else if (v.includes('math education'))      { translated = '수학교육'; }
    else if (v.includes('science education'))   { translated = '과학교육'; }
    else if (v.includes('education'))           { translated = '교육학'; }

    // IT/이공계
    else if (v.includes('artificial intelligence'))                        { translated = '인공지능'; }
    else if (v.includes('machine learning') || v.includes(' ml ') || v === 'ml') { translated = '머신러닝'; }
    else if (v.includes('robotics'))                                       { translated = '로보틱스'; }
    else if (v.includes('computer science') || v === 'cs')                 { translated = '컴공학'; }
    else if (v.includes('software'))                                       { translated = '소프트웨어'; }
    else if (v.includes('data science'))                                   { translated = '데이터과학'; }
    else if (v === 'it' || v.includes('information technology') || v.includes('information system')) { translated = '정보IT'; }
    else if (v.includes('ai'))                                             { translated = '인공지능'; }
    else if (v.includes('biotechnology'))  { translated = '생명공학'; }
    else if (v.includes('biomedical'))     { translated = '생의학'; }
    else if (v.includes('microbiology'))   { translated = '미생물학'; }
    else if (v.includes('biology') || v.includes(' bio') || v === 'bio') { translated = '생물학'; }
    else if (v.includes('chemistry') || v === 'chem') { translated = '화학'; }
    else if (v.includes('physics'))        { translated = '물리학'; }
    else if (v.includes('mathematics') || v.includes('math')) { translated = '수학'; }
    else if (v.includes('statistics'))     { translated = '통계학'; }
    else if (v.includes('actuarial'))      { translated = '보험계리'; }
    else if (v.includes('engineering') || v === 'engr') { translated = '공학'; }
    else if (v.includes('geology'))        { translated = '지질학'; }
    else if (v.includes('earth science'))  { translated = '지구과학'; }
    else if (v.includes('life science'))   { translated = '생명과학'; }
    else if (v.includes('environmental science')) { translated = '환경과학'; }

    // 인문/사회/경영
    else if (v.includes('psychology'))     { translated = '심리학'; }
    else if (v.includes('sociology'))      { translated = '사회학'; }
    else if (v.includes('social work') || v.includes('social welfare')) { translated = '사회복지'; }
    else if (v.includes('social science')) { translated = '사회과학'; }
    else if (v.includes('english literature') || v.includes('literature')) { translated = '영문학'; }
    else if (v.includes('linguistics'))    { translated = '언어학'; }
    else if (v.includes('english'))        { translated = '영어'; }
    else if (v.includes('philosophy'))     { translated = '철학'; }
    else if (v.includes('history'))        { translated = '역사학'; }
    else if (v.includes('law') || v.includes('legal')) { translated = '법학'; }
    else if (v.includes('political science') || v.includes('poli sci')) { translated = '정치학'; }
    else if (v.includes('international') || v.includes('global')) { translated = '국제학'; }
    else if (v.includes('foreign relations')) { translated = '외교학'; }
    else if (v.includes('communications')) { translated = '커뮤니'; }
    else if (v.includes('journalism'))     { translated = '언론학'; }
    else if (v.includes('business'))       { translated = '경영학'; }
    else if (v.includes('economics'))      { translated = '경제학'; }
    else if (v.includes('marketing'))      { translated = '마케팅'; }
    else if (v.includes('commerce'))       { translated = '상업'; }
    else if (v.includes('hospitality'))    { translated = '호텔경영'; }
    else if (v.includes('tourism'))        { translated = '관광학'; }
    else if (v.includes('nursing'))        { translated = '간호학'; }
    else if (v.includes('health care') || v.includes('healthcare')) { translated = '보건학'; }

    // 예술계열 (art 최후방 고정)
    else if (v.includes('fine arts'))              { translated = '순수미술'; }
    else if (v.includes('design'))                 { translated = '디자인'; }
    else if (v.includes('music'))                  { translated = '음악'; }
    else if (v.includes('theater') || v.includes('drama')) { translated = '연극'; }
    else if (v.includes('art'))                    { translated = '예술'; }
    else if (v.includes('studies'))                { translated = '연구'; }
    else if (v.includes('science'))                { translated = '자연과학'; }

    // 국가/민족
    else if (value.includes("Black or African American"))           { translated = '흑인'; }
    else if (value.includes("Hispanic or Latino"))                  { translated = '라틴계'; }
    else if (value.includes("Mixed or Multiracial"))                { translated = '혼혈'; }
    else if (value.includes("Native American"))                     { translated = '미국원주민'; }
    else if (value.includes("Pacific Islander"))                    { translated = '태평원주민'; }
    else if (value.includes("White or European"))                   { translated = '백인유럽'; }
    else if (value.includes("Middle Eastern or North African"))     { translated = '중동아프'; }
    else if (value.includes("Chinese, Hong Kong, or Taiwanese"))   { translated = '중국홍콩등'; }
    else if (value.includes("Japanese"))                            { translated = '일본계'; }
    else if (value.includes("Korean"))                              { translated = '한국'; }
    else if (value.includes("Mongolian or Other East Asian"))       { translated = '동아시아'; }
    else if (value.includes("Indian"))                              { translated = '인도'; }
    else if (value.includes("Pakistani, Afghan, Bangladeshi"))      { translated = '파키등'; }
    else if (value.includes("F (Korean diaspora"))                  { translated = '교포'; }
    else if (value.includes("Prefer not to disclose"))              { translated = '비공개'; }
    else if (value.includes("Prefer not to respond"))               { translated = '성별X'; }
    else if (v.includes("united kingdom") || v === "uk" || v.includes("england")) { translated = '영국'; }
    else if (v.includes("united states") || v.includes("u.s.a") || v.includes("usa") || v.includes("america") || v.includes("united state")) { translated = '미국'; }
    else if (v.includes("canada"))      { translated = '캐나다'; }
    else if (v.includes("ireland"))     { translated = '아일랜드'; }
    else if (v.includes("australia"))   { translated = '호주'; }
    else if (v.includes("new zealand")) { translated = '뉴질랜드'; }
    else if (v.includes("south africa") || v.includes("johannesburg") || v.includes("cape town")) { translated = '남아공'; }
    else if (v.includes("south korea")) { translated = '한국'; }

    // 경력
    else if (v.includes('less than 6 months'))   { translated = '단기'; }
    else if (v.includes('6 months to 1 year'))   { translated = '1년미만'; }
    else if (v.includes('over 1 year'))          { translated = '1년'; }
    else if (v.includes('over 2 year'))          { translated = '2년'; }
    else if (v.includes('over 3 year'))          { translated = '3년'; }
    else if (v.includes('over 4 year'))          { translated = '4년'; }
    else if (v.includes('over 5 year'))          { translated = '5년'; }
    else if (v.includes('over 6 year'))          { translated = '6년'; }
    else if (v.includes('over 7 year'))          { translated = '7년'; }
    else if (v.includes('over 8 year'))          { translated = '8년'; }
    else if (v.includes('over 9 year'))          { translated = '9년'; }
    else if (v.includes('over 10 year'))         { translated = '10년'; }
    else if (v.includes('over 11 year'))         { translated = '11년'; }
    else if (v.includes('over 12 year'))         { translated = '12년'; }
    else if (v.includes('over 13 year'))         { translated = '13년'; }
    else if (v.includes('over 14 year'))         { translated = '14년'; }
    else if (v.includes('over 15 year'))         { translated = '15년'; }
    else if (v.includes('over 20 year'))         { translated = '20년'; }
    else if (v.includes('overseas full-time teaching experience only')) { translated = '해외만'; }

    // 비자/건강/타투
    else if (v.includes("already have a valid visa") || v.includes("already have a residence visa")) { translated = '있음'; }
    else if (v.includes("need a new e2 visa") || v.includes("need a new visa")) { translated = '필요'; }
    else if (v.includes("zero tattoos or piercings"))  { translated = '노타피'; }
    else if (v.includes("visible but can be covered")) { translated = '커버가능'; }
    else if (v.includes("visible tattoo"))             { translated = '왕타투'; }
    else if (v.includes("facial piercings"))           { translated = '얼굴피어'; }
    else if (v === "yes")                              { translated = '있음'; }
    else if (v === "no")                               { translated = '없음'; }
    else if (v.includes("normal") || v.includes("healthy") || v.includes("i have not")) { translated = '건강'; }
    else if (v.includes("i have a condition"))         { translated = '질환'; }
    else if (v.includes("prefer not to say"))          { translated = '건강비공'; }
    else if (v.includes("clean record"))               { translated = '없음'; }
    else if (v.includes("i have a record"))            { translated = '범죄'; }
    else if (v.includes("prefer not to answer"))       { translated = '범죄비밀'; }

    // 종교/성별
    else if (v.includes("irreligious"))   { translated = '무교'; }
    else if (v.includes("christianity")) { translated = '크리'; }
    else if (v.includes("buddhism"))     { translated = '불교'; }
    else if (v.includes("judaism"))      { translated = '유대교'; }
    else if (v.includes("islam"))        { translated = '이슬람'; }
    else if (v.includes("hinduism"))     { translated = '힌두'; }
    else if (v.includes("specific beliefs")) { translated = '사이비'; }
    else if (v === "male")   { translated = '남성'; }
    else if (v === "female") { translated = '여성'; }

    // 주거
    else if (v.includes("school provided housing")) { translated = '숙소희망'; }
    else if (v.includes("enough deposit"))          { translated = '월세희망'; }
    else if (v.includes("housing so no support"))   { translated = '불필요'; }
    else if (v.includes("willing to pay monthly"))  { translated = '추가금'; }

    // 고용/서류 상태
    else if (v.includes("school is aware"))              { translated = '원장안다'; }
    else if (v.includes("not working in korea"))         { translated = '일안함'; }
    else if (v.includes("do not know"))                  { translated = '절대모름'; }
    else if (v.includes("inform them very soon"))        { translated = '곧알림'; }
    else if (v.includes("letter of release"))            { translated = 'LOR'; }
    else if (v.includes("all documents completed"))      { translated = '서류완료'; }
    else if (v.includes("final apostille stage"))        { translated = '준비중'; }
    else if (v.includes("never applied for any documents")) { translated = '준비X'; }
    else if (v.includes("expires within 2 years"))       { translated = '곧만료'; }
    else if (v.includes("valid for more than 2 years"))  { translated = '유효'; }
    else if (v === "recorded")                           { translated = 'E기록ㅇ'; }
    else if (v.includes("issued and apostille completed")){ translated = 'CRC완'; }

    // 가족/반려동물
    else if (v.includes('single'))       { translated = '미혼'; }
    else if (v.includes('married'))      { translated = '기혼'; }
    else if (v.includes('dependents'))   { translated = '부양가족'; }
    else if (v.includes('divorced'))     { translated = '이혼'; }
    else if (v.includes('coming alone')) { translated = '혼자'; }
    else if (v.includes('young children'))       { translated = '애있음'; }
    else if (v.includes('school age children'))  { translated = '가족있음'; }
    else if (v.includes("dog"))  { translated = '강아지'; }
    else if (v.includes("cat"))  { translated = '고양이'; }
    else if (v.includes('other pets')) { translated = '동물'; }

    // 유입경로
    else if (value.includes("Friend Referral"))   { translated = '친구추천'; }
    else if (value.includes("Previous Experience")){ translated = '과거'; }
    else if (v.includes("google"))    { translated = '구글'; }
    else if (v.includes("reddit"))    { translated = '레딧'; }
    else if (v.includes("facebook"))  { translated = '페북'; }
    else if (v.includes("instagram")) { translated = '인스타'; }
    else if (v.includes("youtube"))   { translated = '유튜브'; }
    else if (value.includes("ESL Cafe")) { translated = 'ESL카페'; }
    else if (v.includes("linkedin"))  { translated = '링크드인'; }
    else if (value.includes("Other")) { translated = '기타'; }

    // Agreement
    else if (v === "i agree")              { translated = '동의'; }
    else if (v.includes("i do not agree")) { translated = '거절'; }

    translatedValues.push(translated);
  }

  const stickWords = ["유", "초", "중", "고", "성", "무관", "수도", "중도", "소도"];
  const allStick = translatedValues.length > 0 && translatedValues.every(t => stickWords.includes(t));
  return allStick ? translatedValues.join('') : translatedValues.join(', ');
}


//=========================================================
// ---------------------- 10. 사진 자동 삽입 (Photo Auto-Insert) ----------------------
// 기존 코드 무변경. onFormSubmit에서 insertIntoWaitSheet 후 호출됨.
//=========================================================

var PHOTO_CONFIG = {
  ARCHIVE_FOLDER: 'Photo_Archive',
  ROW_HEIGHT: 80,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_MIME_PREFIX: 'image/',
  FILE_ID_PATTERN: /^[a-zA-Z0-9_-]+$/
};

/**
 * New 시트에 방금 삽입된 행의 Photo 컬럼(C열)에 사진을 삽입합니다.
 * sourceData[3] = "Attach your files" (Drive URL)
 * @param {Array} sourceData - Form 시트에서 가져온 원본 데이터
 * @param {Sheet} targetSheet - New 시트
 */
function processNewRowPhoto(sourceData, targetSheet) {
  try {
    var lastRow = targetSheet.getLastRow();
    if (lastRow < 2) return;

    var photoCol = 3; // New 시트의 Photo 컬럼 (C열)
    var nameCol = 2;  // New 시트의 Full name 컬럼 (B열)

    // sourceData[3] = "Attach your files" 필드 (Drive URL)
    var attachUrl = String(sourceData[3] || '');

    if (!attachUrl || !attachUrl.match(/drive\.google\.com|docs\.google\.com/)) {
      targetSheet.getRange(lastRow, photoCol).setValue('No Photo');
      targetSheet.setRowHeight(lastRow, PHOTO_CONFIG.ROW_HEIGHT);
      Logger.log('Photo: No Drive URL found in Attach field');
      return;
    }

    // Drive URL에서 파일 ID 추출
    var fileId = extractPhotoFileId_(attachUrl);
    if (!fileId) {
      targetSheet.getRange(lastRow, photoCol).setValue('No Photo');
      targetSheet.setRowHeight(lastRow, PHOTO_CONFIG.ROW_HEIGHT);
      Logger.log('Photo: Cannot parse file ID from: ' + attachUrl);
      return;
    }

    // 파일 ID 정규식 검증
    if (!PHOTO_CONFIG.FILE_ID_PATTERN.test(fileId)) {
      targetSheet.getRange(lastRow, photoCol).setValue('No Photo');
      Logger.log('Photo: Invalid file ID pattern: ' + fileId);
      return;
    }

    // Drive 파일 접근
    var file;
    try {
      file = DriveApp.getFileById(fileId);
    } catch (err) {
      targetSheet.getRange(lastRow, photoCol).setValue('No Photo');
      Logger.log('Photo: Cannot access file: ' + fileId + ' - ' + err.message);
      return;
    }

    // MIME 타입 검증 (이미지만)
    var mimeType = file.getMimeType();
    if (!mimeType || mimeType.indexOf(PHOTO_CONFIG.ALLOWED_MIME_PREFIX) !== 0) {
      // 이미지가 아니면 폴더 내 이미지 검색 시도
      var imageFile = findImageInFolder_(fileId);
      if (imageFile) {
        file = imageFile;
        fileId = file.getId();
        mimeType = file.getMimeType();
      } else {
        targetSheet.getRange(lastRow, photoCol).setValue('No Photo');
        Logger.log('Photo: Not an image: ' + mimeType);
        return;
      }
    }

    // 파일 크기 검증 (10MB)
    if (file.getSize() > PHOTO_CONFIG.MAX_FILE_SIZE) {
      targetSheet.getRange(lastRow, photoCol).setValue('No Photo');
      Logger.log('Photo: File too large: ' + (file.getSize() / 1024 / 1024).toFixed(1) + 'MB');
      return;
    }

    // 공유 권한 설정 (IMAGE 함수 작동용)
    try {
      file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    } catch (err) {
      Logger.log('Photo: Cannot set sharing: ' + err.message);
    }

    // Photo_Archive에 복사
    archivePhotoFile_(file, targetSheet, lastRow, nameCol);

    // IMAGE 함수 삽입
    var imageFormula = '=IMAGE("https://drive.google.com/uc?export=view&id=' + fileId + '", 1)';
    targetSheet.getRange(lastRow, photoCol).setFormula(imageFormula);
    targetSheet.setRowHeight(lastRow, PHOTO_CONFIG.ROW_HEIGHT);

    Logger.log('Photo: SUCCESS - inserted for row ' + lastRow + ', fileId: ' + fileId);

  } catch (err) {
    Logger.log('Photo ERROR: ' + err.message);
    // 사진 실패해도 메인 프로세스에 영향 없음
  }
}


/**
 * Drive URL에서 파일 ID 추출
 * @param {string} url
 * @returns {string|null}
 */
function extractPhotoFileId_(url) {
  if (!url) return null;
  url = String(url).trim();

  // open?id=FILE_ID
  var match = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (match) return match[1];

  // /file/d/FILE_ID/ 또는 /d/FILE_ID/
  match = url.match(/\/(?:file\/)?d\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];

  // /folders/FOLDER_ID
  match = url.match(/\/folders\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];

  // 순수 ID (URL이 아닌 경우)
  if (PHOTO_CONFIG.FILE_ID_PATTERN.test(url) && url.length > 10) {
    return url;
  }

  return null;
}


/**
 * 폴더인 경우, 안에서 첫 번째 이미지 파일을 찾아 반환
 * @param {string} folderId
 * @returns {File|null}
 */
function findImageInFolder_(folderId) {
  try {
    var folder = DriveApp.getFolderById(folderId);
    var files = folder.getFiles();
    while (files.hasNext()) {
      var f = files.next();
      if (f.getMimeType().indexOf('image/') === 0) {
        return f;
      }
    }
  } catch (err) {
    // 폴더가 아니면 무시
  }
  return null;
}


/**
 * Photo_Archive 폴더에 {FullName}_{YYYYMMDD}.ext로 복사
 * @param {File} file
 * @param {Sheet} sheet
 * @param {number} row
 * @param {number} nameCol
 */
function archivePhotoFile_(file, sheet, row, nameCol) {
  try {
    var folders = DriveApp.getFoldersByName(PHOTO_CONFIG.ARCHIVE_FOLDER);
    var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(PHOTO_CONFIG.ARCHIVE_FOLDER);

    var fullName = String(sheet.getRange(row, nameCol).getValue() || 'Unknown').trim();
    fullName = fullName.replace(/[^a-zA-Z0-9가-힣\s_-]/g, '').replace(/\s+/g, '_');

    var dateStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd');

    var extMap = {
      'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif',
      'image/webp': '.webp', 'image/bmp': '.bmp', 'image/svg+xml': '.svg'
    };
    var ext = extMap[file.getMimeType()] || '.jpg';

    var archiveName = fullName + '_' + dateStr + ext;
    file.makeCopy(archiveName, folder);
    Logger.log('Photo Archive: ' + archiveName);

  } catch (err) {
    Logger.log('Photo Archive failed: ' + err.message);
  }
}


/**
 * 기존 행 일괄 사진 처리 (backfill)
 * New 시트에서 Photo 컬럼이 'Photo' 또는 비어있는 행을 일괄 처리
 * 메뉴에서 이 함수를 선택하고 실행하세요.
 */
function backfillPhotos() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var formSheet = ss.getSheetByName(sh_name_form);
    var newSheet = ss.getSheetByName(sh_name_wait);

    if (!newSheet || !formSheet) {
      Logger.log('backfillPhotos: Sheet not found');
      return;
    }

    var lastRow = newSheet.getLastRow();
    if (lastRow < 2) {
      SpreadsheetApp.getUi().alert('처리할 행이 없습니다.');
      return;
    }

    var photoCol = 3;
    var emailCol = 1;
    var processed = 0, skipped = 0, errors = 0;

    // Form 시트에서 이메일→첨부파일 매핑 구축
    var formData = formSheet.getDataRange().getValues();
    var emailToAttach = {};
    for (var i = 1; i < formData.length; i++) {
      var email = String(formData[i][1] || '').trim().toLowerCase();
      var attach = String(formData[i][3] || '');
      if (email && attach) {
        emailToAttach[email] = attach;
      }
    }

    for (var row = 2; row <= lastRow; row++) {
      try {
        var photoValue = String(newSheet.getRange(row, photoCol).getValue() || '');

        // 이미 IMAGE 수식이 있으면 스킵
        var formula = newSheet.getRange(row, photoCol).getFormula();
        if (formula && formula.indexOf('IMAGE') !== -1) {
          skipped++;
          continue;
        }

        // Photo 또는 빈 값인 경우만 처리
        if (photoValue !== 'Photo' && photoValue !== '' && photoValue !== 'No Photo') {
          skipped++;
          continue;
        }

        // New 시트의 이메일로 Form 시트 첨부파일 URL 찾기
        var rowEmail = String(newSheet.getRange(row, emailCol).getValue() || '').trim().toLowerCase();
        var attachUrl = emailToAttach[rowEmail] || '';

        if (!attachUrl || !attachUrl.match(/drive\.google\.com|docs\.google\.com/)) {
          newSheet.getRange(row, photoCol).setValue('No Photo');
          newSheet.setRowHeight(row, PHOTO_CONFIG.ROW_HEIGHT);
          skipped++;
          continue;
        }

        // 사진 처리 (processNewRowPhoto와 동일 로직)
        var fileId = extractPhotoFileId_(attachUrl);
        if (!fileId || !PHOTO_CONFIG.FILE_ID_PATTERN.test(fileId)) {
          newSheet.getRange(row, photoCol).setValue('No Photo');
          newSheet.setRowHeight(row, PHOTO_CONFIG.ROW_HEIGHT);
          skipped++;
          continue;
        }

        var file;
        try { file = DriveApp.getFileById(fileId); }
        catch (err) {
          var imageFile = findImageInFolder_(fileId);
          if (imageFile) { file = imageFile; fileId = file.getId(); }
          else { newSheet.getRange(row, photoCol).setValue('No Photo'); skipped++; continue; }
        }

        var mimeType = file.getMimeType();
        if (!mimeType || mimeType.indexOf('image/') !== 0) {
          var imageFile2 = findImageInFolder_(fileId);
          if (imageFile2) { file = imageFile2; fileId = file.getId(); }
          else { newSheet.getRange(row, photoCol).setValue('No Photo'); skipped++; continue; }
        }

        if (file.getSize() > PHOTO_CONFIG.MAX_FILE_SIZE) {
          newSheet.getRange(row, photoCol).setValue('No Photo'); skipped++; continue;
        }

        try { file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); }
        catch (err) { /* 무시 */ }

        archivePhotoFile_(file, newSheet, row, 2);

        var imageFormula = '=IMAGE("https://drive.google.com/uc?export=view&id=' + fileId + '", 1)';
        newSheet.getRange(row, photoCol).setFormula(imageFormula);
        newSheet.setRowHeight(row, PHOTO_CONFIG.ROW_HEIGHT);
        processed++;

      } catch (err) {
        errors++;
        Logger.log('backfillPhotos row ' + row + ' error: ' + err.message);
      }
    }

    var summary = '완료!\n처리: ' + processed + ' / 스킵: ' + skipped + ' / 에러: ' + errors;
    SpreadsheetApp.getUi().alert(summary);
    Logger.log('backfillPhotos: ' + summary);

  } catch (err) {
    Logger.log('backfillPhotos ERROR: ' + err.message);
    SpreadsheetApp.getUi().alert('오류: ' + err.message);
  }
}


