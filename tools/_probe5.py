import requests, re

# main bundle에서 API 경로 추출
url = "https://blackkiwi.net/main.3c2adc043e4085fe7b5d.js"
js = requests.get(url, timeout=15).text

# /api/ 경로 패턴
api_paths = re.findall(r'["\`](/api/[^"\'`\s]{3,60})["\`]', js)
print("API paths:", sorted(set(api_paths))[:30])

# keyword 관련
kw_routes = [a for a in set(api_paths) if "keyword" in a.lower() or "search" in a.lower() or "trend" in a.lower()]
print("\nKeyword routes:", kw_routes)

# fetch/axios 호출 패턴
calls = re.findall(r'\.get\(["\`](/[^"\'`]+)["\`]', js)
print("\nGET calls:", sorted(set(calls))[:20])
