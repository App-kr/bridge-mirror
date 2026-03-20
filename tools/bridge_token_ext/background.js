// Bridge ImageFX Token Auto-Refresh
// labs.google 세션에서 토큰을 가져와 localhost:8765 서버로 전송

const SERVER = "http://localhost:8765";
const SESSION_URL = "https://labs.google/fx/api/auth/session";

async function refreshToken() {
  try {
    // 1. ImageFX 세션 토큰 가져오기
    const resp = await fetch(SESSION_URL, { credentials: "include" });
    if (!resp.ok) return;
    const data = await resp.json();
    if (!data.access_token) return;

    // 2. 로컬 서버로 전송
    await fetch(SERVER + "/api/set-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token: data.access_token,
        expires: data.expires
      })
    });
    console.log("[Bridge] Token refreshed");
  } catch (e) {
    // 서버 미실행 또는 미로그인 — 무시
  }
}

// 설치 시 즉시 실행
chrome.runtime.onInstalled.addListener(() => {
  refreshToken();
  // 25분마다 갱신 (토큰 ~50분 유효)
  chrome.alarms.create("refresh", { periodInMinutes: 25 });
});

// 브라우저 시작 시
chrome.runtime.onStartup.addListener(() => {
  refreshToken();
});

// 알람 실행
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "refresh") refreshToken();
});
