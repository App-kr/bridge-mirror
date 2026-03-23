/**
 * BRIDGE Meet Room 10개 생성
 * ===========================
 * 1. https://script.google.com 접속 (Google 로그인 상태)
 * 2. "새 프로젝트" 클릭
 * 3. 기존 코드 전부 지우고 이 코드 전체 붙여넣기
 * 4. ▶ "실행" 버튼 클릭
 * 5. 권한 승인 (최초 1회)
 * 6. "실행 로그" 탭에서 10개 링크 전체 복사
 * 7. BRIDGE 인터뷰 모달에 붙여넣기 → "추가" 클릭
 *
 * 추가 설정 불필요 — 그대로 실행하면 됩니다.
 */

function createMeetRooms() {
  // CalendarApp 호출로 calendar 권한 자동 획득
  CalendarApp.getDefaultCalendar();
  var token = ScriptApp.getOAuthToken();
  var links = [];

  Logger.log("Meet 회의실 10개 생성 시작...\n");

  for (var i = 1; i <= 10; i++) {
    var start = new Date(2099, 0, i, 10, 0, 0);
    var end = new Date(2099, 0, i, 11, 0, 0);

    var event = {
      summary: "BRIDGE Interview Room " + i,
      description: "Bridge Recruitment permanent interview room",
      start: { dateTime: start.toISOString(), timeZone: "Asia/Seoul" },
      end: { dateTime: end.toISOString(), timeZone: "Asia/Seoul" },
      conferenceData: {
        createRequest: {
          conferenceSolutionKey: { type: "hangoutsMeet" },
          requestId: "bridge-room-" + i + "-" + Date.now()
        }
      }
    };

    try {
      var res = UrlFetchApp.fetch(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1",
        {
          method: "post",
          contentType: "application/json",
          headers: { Authorization: "Bearer " + token },
          payload: JSON.stringify(event),
          muteHttpExceptions: true
        }
      );

      var data = JSON.parse(res.getContentText());

      if (res.getResponseCode() !== 200) {
        Logger.log("Room " + i + ": ERROR - " + (data.error ? data.error.message : "Unknown"));
        continue;
      }

      var meetLink = data.hangoutLink || "";
      if (!meetLink && data.conferenceData && data.conferenceData.entryPoints) {
        for (var j = 0; j < data.conferenceData.entryPoints.length; j++) {
          if (data.conferenceData.entryPoints[j].entryPointType === "video") {
            meetLink = data.conferenceData.entryPoints[j].uri;
            break;
          }
        }
      }

      if (meetLink) {
        links.push(meetLink);
        Logger.log("Room " + i + ": " + meetLink);
      } else {
        Logger.log("Room " + i + ": WARNING - 링크 없음");
      }
    } catch(e) {
      Logger.log("Room " + i + ": ERROR - " + e.message);
    }
  }

  Logger.log("\n" + "=".repeat(50));
  Logger.log("완료: " + links.length + " / 10 rooms");
  Logger.log("=".repeat(50));

  if (links.length > 0) {
    Logger.log("\n아래 링크를 전체 복사 → BRIDGE 인터뷰 모달에 붙여넣기:\n");
    Logger.log(links.join("\n"));
  }
}
