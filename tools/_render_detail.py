"""
Render API 상세 확인 - disk + env vars 전체
"""
import os, sys, json
sys.path.insert(0, r"Q:\Claudework\bridge base")

from tools import bx as bx_mod
bx_mod.cmd_load()

RENDER_API_KEY = os.environ.get("RENDER_API_KEY")
if not RENDER_API_KEY:
    print("ERROR: RENDER_API_KEY not found")
    sys.exit(1)

import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

SVC_ID = "srv-d6imvn1aae7s73ck5570"

# Full service detail
print("=== Service Detail ===")
svc = fetch(f"https://api.render.com/v1/services/{SVC_ID}")
plan = svc.get("service", svc).get("plan", "?")
print(f"Plan: {plan}")
print(f"Type: {svc.get('service', svc).get('type', '?')}")

# Full env vars (no truncation)
print("\n=== All Env Vars (DB/AWS related) ===")
envs = fetch(f"https://api.render.com/v1/services/{SVC_ID}/env-vars")
for e in (envs if isinstance(envs, list) else []):
    k = e.get("envVar", {}).get("key", "?")
    v = e.get("envVar", {}).get("value", None)
    if any(x in k for x in ["DB", "AWS", "BUCKET", "REGION"]):
        display = v if v else "[secret/null]"
        print(f"  {k} = {display}")

# Try different disk endpoints
print("\n=== Disk check ===")
for path in [
    f"https://api.render.com/v1/services/{SVC_ID}/disks",
    f"https://api.render.com/v1/disks?serviceId={SVC_ID}",
]:
    try:
        d = fetch(path)
        print(f"  {path}: {json.dumps(d)[:200]}")
    except Exception as ex:
        print(f"  {path}: {ex}")
