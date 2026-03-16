import requests, re

# main.*.js 직접 탐색
r = requests.get("https://blackkiwi.net", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
scripts = re.findall(r'src="(/[^"]+\.js)"', r.text)
print("All scripts:", scripts)

# main bundle 찾기
main_scripts = [s for s in scripts if "main" in s or "app" in s]
if not main_scripts:
    main_scripts = scripts[-3:]  # 마지막 3개 시도

for s in main_scripts[:3]:
    url = "https://blackkiwi.net" + s
    print(f"\nTrying: {url}")
    try:
        js = requests.get(url, timeout=10).text
        # API URL 패턴
        apis = re.findall(r'["\`](https?://[a-zA-Z0-9./_-]{10,80})["\`]', js)
        api_set = set(a for a in apis if "blackkiwi" in a or "api" in a.lower())
        for a in list(api_set)[:15]:
            print("  API:", a)
        # baseURL
        bases = re.findall(r'baseURL["\s:=]+["\`]([^"\`]+)["\`]', js)
        for b in bases[:5]:
            print("  baseURL:", b)
        print(f"  JS size: {len(js)}")
    except Exception as e:
        print(f"  ERR: {e}")
