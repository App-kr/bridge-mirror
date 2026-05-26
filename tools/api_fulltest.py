#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRIDGE API 전수 검사 스크립트 - 10회 이상 반복 테스트"""
import sys
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, 'Q:/Claudework/bridge base/tools')
from bx import _read

ADMIN_KEY = _read('ADMIN_API_KEY')
BASE = 'https://bridge-n7hk.onrender.com'
FRONTEND = 'https://bridge-chi-lime.vercel.app'

ENDPOINTS = [
    # (label, method, path, needs_auth, body)
    # --- 공개 API ---
    ('PUBLIC', 'GET', '/api/jobs?limit=5', False, None),
    ('PUBLIC', 'GET', '/api/testimonials?limit=5', False, None),
    ('PUBLIC', 'GET', '/api/community/korea?limit=5', False, None),
    ('PUBLIC', 'GET', '/api/community/visa?limit=5', False, None),
    ('PUBLIC', 'GET', '/api/community/tips?limit=5', False, None),
    ('PUBLIC', 'GET', '/api/community/support?limit=5', False, None),
    # --- 관리자 GET API ---
    ('ADMIN',  'GET', '/api/admin/candidates?limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/candidates?limit=5&search=test', True, None),
    ('ADMIN',  'GET', '/api/admin/employers?limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/jobs?limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/applications?limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/community/posts?limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/community/posts?board=visa&limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/banners', True, None),
    ('ADMIN',  'GET', '/api/admin/site-settings', True, None),
    ('ADMIN',  'GET', '/api/admin/mail/introduce-log?limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/employers-for-mail?limit=5', True, None),
    ('ADMIN',  'GET', '/api/admin/db/status', True, None),
    # --- 관리자 쓰기 ---
    ('WRITE',  'POST', '/api/admin/reset-blacklist', True, b'{}'),
    # --- 프론트엔드 ---
    ('FRONT',  'GET', '/admin', False, None),
]

def make_request(method, url, headers, body=None, timeout=30):
    req = urllib.request.Request(url, headers=headers, method=method, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            raw = resp.read(2000)
            # count items if JSON
            count_str = ''
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    count_str = f'({len(data)}건)'
                elif isinstance(data, dict):
                    for k in ('items', 'data', 'candidates', 'jobs', 'posts', 'results', 'employers'):
                        if k in data and isinstance(data[k], list):
                            count_str = f'({len(data[k])}건)'
                            break
                    else:
                        count_str = '(obj)'
            except Exception:
                count_str = f'({len(raw)}bytes)'
            return code, count_str, None
    except urllib.error.HTTPError as e:
        body_preview = ''
        try:
            body_preview = e.read(300).decode('utf-8', errors='replace')
        except Exception:
            pass
        return e.code, '', body_preview[:100]
    except Exception as ex:
        return 0, '', str(ex)[:100]

def run_round(round_num, results_agg):
    print(f'\n{"="*60}')
    print(f'[ROUND {round_num}]')
    print(f'{"="*60}')

    round_results = {}

    for (label, method, path, needs_auth, body) in ENDPOINTS:
        # 프론트엔드는 별도 base
        if label == 'FRONT':
            url = FRONTEND + path
        else:
            url = BASE + path

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json, text/html, */*',
        }
        if needs_auth:
            headers['X-Admin-Key'] = ADMIN_KEY
        if body:
            headers['Content-Type'] = 'application/json'

        code, count, err = make_request(method, url, headers, body)

        ok = '✅' if 200 <= code < 300 else '❌'
        err_str = f' | ERR: {err}' if err else ''
        label_short = f'{method} {path[:55]}'
        print(f'  {ok} [{label}] {label_short:<60} : {code} {count}{err_str}')

        key = (method, path)
        if key not in results_agg:
            results_agg[key] = []
        results_agg[key].append((round_num, code, count, err))
        round_results[key] = (code, err)

    return round_results

def main():
    print('BRIDGE API 전수 검사 시작')
    print(f'Backend : {BASE}')
    print(f'Frontend: {FRONTEND}')
    print(f'Key     : {ADMIN_KEY[:8]}...')

    results_agg = {}
    all_round_results = []

    TOTAL_ROUNDS = 10

    for rnd in range(1, TOTAL_ROUNDS + 1):
        rr = run_round(rnd, results_agg)
        all_round_results.append(rr)
        if rnd < TOTAL_ROUNDS:
            time.sleep(1.5)  # 서버 부하 방지

    # 실패한 항목 3회 추가 재시도
    failures = {}
    for (method, path), rounds_data in results_agg.items():
        failed = [(r, c, e) for (r, c, cnt, e) in rounds_data if not (200 <= c < 300)]
        if failed:
            failures[(method, path)] = failed

    if failures:
        print(f'\n{"="*60}')
        print('[실패 항목 추가 재시도 - 3회]')
        print(f'{"="*60}')
        for (method, path), fail_list in failures.items():
            needs_auth = any(e[0] for e in ENDPOINTS if e[1]==method and e[2]==path)
            body = next((e[4] for e in ENDPOINTS if e[1]==method and e[2]==path), None)
            label = next((e[0] for e in ENDPOINTS if e[1]==method and e[2]==path), 'UNK')

            if label == 'FRONT':
                url = FRONTEND + path
            else:
                url = BASE + path

            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json, text/html, */*',
            }
            if needs_auth:
                headers['X-Admin-Key'] = ADMIN_KEY
            if body:
                headers['Content-Type'] = 'application/json'

            for retry in range(1, 4):
                code, count, err = make_request(method, url, headers, body)
                ok = '✅' if 200 <= code < 300 else '❌'
                err_str = f' | {err}' if err else ''
                print(f'  {ok} RETRY-{retry} {method} {path[:55]:<55} : {code} {count}{err_str}')
                results_agg[(method, path)].append(('R'+str(retry), code, count, err))
                time.sleep(1)

    # 최종 요약 표
    print(f'\n{"="*60}')
    print('[최종 결과 요약]')
    print(f'{"="*60}')
    print(f'{"엔드포인트":<60} | {"성공":<4} | {"실패":<4} | {"상태"}')
    print('-'*90)

    final_failures = []
    for (method, path), rounds_data in results_agg.items():
        success = sum(1 for (_, c, _, _) in rounds_data if 200 <= c < 300)
        fail    = sum(1 for (_, c, _, _) in rounds_data if not (200 <= c < 300))
        total   = success + fail
        status = '✅ ALL OK' if fail == 0 else (f'⚠️  {fail}/{total} 실패' if success > 0 else f'❌ ALL FAIL')

        codes = list({c for (_, c, _, _) in rounds_data})
        errs  = list({e for (_, _, _, e) in rounds_data if e})

        label_str = f'{method} {path[:55]}'
        print(f'{label_str:<60} | {success:<4} | {fail:<4} | {status}')

        if fail > 0:
            final_failures.append({
                'endpoint': f'{method} {path}',
                'codes': codes,
                'errors': errs,
                'attempts': total,
                'fail_count': fail,
            })

    if final_failures:
        print(f'\n{"="*60}')
        print('[최종 실패 목록]')
        print(f'{"="*60}')
        print(f'{"엔드포인트":<60} | {"에러코드":<15} | {"에러내용":<40} | 재시도횟수')
        print('-'*130)
        for f in final_failures:
            codes_str = ','.join(str(c) for c in f['codes'])
            errs_str  = ' / '.join(f['errors'])[:40] if f['errors'] else '-'
            print(f'{f["endpoint"][:60]:<60} | {codes_str:<15} | {errs_str:<40} | {f["attempts"]}')
    else:
        print('\n🎉 모든 엔드포인트 전수 검사 통과!')

    print(f'\n총 {TOTAL_ROUNDS}라운드 × {len(ENDPOINTS)}개 엔드포인트 = {TOTAL_ROUNDS*len(ENDPOINTS)}회 테스트 완료')

if __name__ == '__main__':
    main()
