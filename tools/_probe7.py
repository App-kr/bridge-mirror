import requests, json

kw = "\uc6d0\uc5b4\ubbfc\uac15\uc0ac"  # 원어민강사
base = "https://blackkiwi.net"
hdrs = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://blackkiwi.net/"}

# integrated-related-keywords 전체 데이터 확인
r = requests.get(f"{base}/api/service/keyword/naver/integrated-related-keywords?keyword={requests.utils.quote(kw)}&limit=20", headers=hdrs, timeout=8)
print("Status:", r.status_code)
data = r.json()
print("Total:", data.get("total"))
for item in data.get("list", [])[:10]:
    print(f"  {item['keyword']:<25} PC:{item.get('pcVolume',0):>5} Mobile:{item.get('mobileVolume',0):>5} sim:{item.get('similarityScore',0)}")

# 다른 키워드도 테스트
for seed in ["\uc6d0\uc5b4\ubbfc\ucc44\uc6a9", "\uc601\uc5b4\ud559\uc6d0\uc6d0\uc5b4\ubbfc"]:
    r2 = requests.get(f"{base}/api/service/keyword/naver/integrated-related-keywords?keyword={requests.utils.quote(seed)}&limit=10", headers=hdrs, timeout=8)
    d2 = r2.json()
    print(f"\n[{seed}] total={d2.get('total')}")
    for item in d2.get("list", [])[:5]:
        print(f"  {item['keyword']:<25} PC:{item.get('pcVolume',0):>5} Mobile:{item.get('mobileVolume',0):>5}")
