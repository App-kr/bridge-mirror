import requests, re, json

kw = "\uc6d0\uc5b4\ubbfc\uac15\uc0ac"  # 원어민강사

# Blackkiwi JS 번들에서 API 엔드포인트 찾기
r = requests.get("https://blackkiwi.net", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
scripts = re.findall(r'<script[^>]*src="(/[^"]+\.js)"', r.text)

for s in scripts[:5]:
    try:
        url = "https://blackkiwi.net" + s
        js = requests.get(url, timeout=8).text
        # API base URL 탐색
        apis = re.findall(r'["\'](https?://[^"\']+blackkiwi[^"\']{0,80})["\']', js)
        if apis:
            print(f"Script {s}:")
            for a in set(apis[:10]):
                print(f"  {a}")
        # axios baseURL
        base = re.findall(r'baseURL\s*[:=]\s*["\']([^"\']+)["\']', js)
        if base:
            print(f"  baseURL: {base}")
    except Exception as e:
        print(f"JS fetch err: {e}")
