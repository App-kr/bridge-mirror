& 'Q:\Claudework\ClaudeBlog\.venv\Scripts\python.exe' -X utf8 -c "
import requests, re, json

kw = '원어민강사'
# 1. Blackkiwi 메인 검색
url = f'https://blackkiwi.net/search/?q={requests.utils.quote(kw)}'
r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
print('Blackkiwi search status:', r.status_code)
# JSON 데이터 추출 시도
jsons = re.findall(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', r.text, re.DOTALL)
if jsons:
    print('Found __INITIAL_STATE__:', jsons[0][:500])
else:
    # API 엔드포인트 탐색
    api_patterns = re.findall(r'(https://[^\"]+api[^\"]{0,50})', r.text)
    print('API patterns found:', api_patterns[:5])
    # 키워드 데이터 관련 패턴
    kw_data = re.findall(r'monthlyPcQcCnt|searchCnt|totalCnt|volume|monthlyMobileQcCnt', r.text)
    print('Data fields found:', set(kw_data))
    print('HTML sample:', r.text[1000:2500])
"
