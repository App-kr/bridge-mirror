import requests, re, json

kw = "\uc6d0\uc5b4\ubbfc\uac15\uc0ac"  # 원어민강사

# Blackkiwi API endpoint 탐색
api_candidates = [
    f"https://api.blackkiwi.net/v2/keyword/info?keyword={requests.utils.quote(kw)}",
    f"https://api.blackkiwi.net/api/v1/keyword/search?keyword={requests.utils.quote(kw)}",
    f"https://blackkiwi.net/api/keyword?q={requests.utils.quote(kw)}",
    f"https://api.blackkiwi.net/keyword?keyword={requests.utils.quote(kw)}",
]
hdrs = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://blackkiwi.net/",
    "Accept": "application/json",
}
for url in api_candidates:
    try:
        r = requests.get(url, headers=hdrs, timeout=5)
        print(f"{url[:60]} -> {r.status_code} | {r.text[:200]}")
    except Exception as e:
        print(f"{url[:60]} -> ERR: {type(e).__name__}")

# Naver DataLab 접근 (인증 없이 - 401 확인)
r2 = requests.post(
    "https://openapi.naver.com/v1/datalab/search",
    headers={"X-Naver-Client-Id": "test", "X-Naver-Client-Secret": "test", "Content-Type": "application/json"},
    json={"startDate": "2026-01-01", "endDate": "2026-03-15", "timeUnit": "month",
          "keywordGroups": [{"groupName": kw, "keywords": [kw]}]},
    timeout=5
)
print(f"\nNaver DataLab with test keys: {r2.status_code} | {r2.text[:200]}")
