import requests, re, json

kw = "\uc6d0\uc5b4\ubbfc\uac15\uc0ac"  # 원어민강사

# Blackkiwi search
url = "https://blackkiwi.net/search/?q=" + requests.utils.quote(kw)
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
print("Blackkiwi search status:", r.status_code)

jsons = re.findall(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", r.text, re.DOTALL)
if jsons:
    print("Found __INITIAL_STATE__:", jsons[0][:500])
else:
    api_patterns = re.findall(r'(https://[^"]+api[^"]{0,50})', r.text)
    print("API patterns:", api_patterns[:5])
    kw_data = re.findall(r'monthlyPcQcCnt|searchCnt|totalCnt|volume|monthlyMobileQcCnt', r.text)
    print("Data fields:", set(kw_data))
    # 스크립트 태그 찾기
    scripts = re.findall(r'<script[^>]*src="([^"]+)"', r.text)
    print("Scripts:", scripts[:8])
    print("HTML 1500-3000:")
    print(r.text[1500:3000])
