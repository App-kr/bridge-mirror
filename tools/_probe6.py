import requests, json

kw = "\uc6d0\uc5b4\ubbfc\uac15\uc0ac"  # 원어민강사
hdrs = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": "https://blackkiwi.net/",
}
base = "https://blackkiwi.net"

# lite-analysis 시도
endpoints = [
    ("GET", f"{base}/api/service/keyword/naver/lite-analysis?keyword={requests.utils.quote(kw)}", None),
    ("POST", f"{base}/api/service/keyword/naver/lite-analysis", {"keyword": kw}),
    ("GET", f"{base}/api/service/keyword/naver/integrated-related-keywords?keyword={requests.utils.quote(kw)}", None),
    ("POST", f"{base}/api/service/keyword/naver/custom-search-trend", {"keyword": kw}),
]
for method, url, body in endpoints:
    try:
        if method == "GET":
            r = requests.get(url, headers=hdrs, timeout=6)
        else:
            r = requests.post(url, headers=hdrs, json=body, timeout=6)
        print(f"{method} {url[-60:]} -> {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"{method} {url[-60:]} -> ERR: {type(e).__name__}")
