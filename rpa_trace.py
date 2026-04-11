"""실시간 RPA 실행 추적 — 어디서 막히는지 파악"""
import sys, time
LOG = open("Q:/Claudework/bridge base/logs/rpa_trace.txt", "w", buffering=1)

def log(msg):
    t = time.strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    LOG.write(line + "\n")
    LOG.flush()

log("=== RPA TRACE START ===")

log("1. Loading credentials...")
sys.path.insert(0, "Q:/Claudework/bridge base")

log("2. Importing craigslist_auto_rpa (module-level code runs here)...")
import craigslist_auto_rpa as rpa
log(f"3. Imported OK. CL_EMAIL={rpa.CL_EMAIL}")

log("4. integrity_check...")
result = rpa.integrity_check()
log(f"5. integrity_check result={result}")

log("6. get_ad_jobs...")
jobs = rpa.get_ad_jobs(limit=5)
log(f"7. got {len(jobs)} jobs")

log("8. Generating ad texts...")
for i, job in enumerate(jobs[:3]):
    log(f"  job {i}: {job['job_code']}")
    title, body = rpa.build_ad_text(job)
    log(f"  title={title[:50]}")
    body2, removed = rpa.redact_pii(body)
    log(f"  redact removed={len(removed)}")
    ok = rpa.security_check(body2, job['job_code'])
    log(f"  security_check={ok}")

log("9. Building driver (Chrome start)...")
driver = rpa.build_driver(headless=True, account="default")
log(f"10. Driver OK: {driver.session_id}")

log("11. cl_login...")
login_ok = rpa.cl_login(driver)
log(f"12. login={login_ok}")

driver.quit()
log("=== DONE ===")
LOG.close()
