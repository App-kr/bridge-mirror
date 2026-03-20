// Bridge ImageFX — content script
// localhost:8765 페이지 로드 시 background에 즉시 토큰 갱신 요청
chrome.runtime.sendMessage({ action: "refreshNow" });
