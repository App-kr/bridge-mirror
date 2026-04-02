"""
Render API로 bridge-api 서비스 상태 + disk 확인
"""
import os, sys, json
sys.path.insert(0, r"Q:\Claudework\bridge base")

from tools import bx as bx_mod
bx_mod.cmd_load()

RENDER_API_KEY = os.environ.get("RENDER_API_KEY")
if not RENDER_API_KEY:
    print("ERROR: RENDER_API_KEY not in BX vault")
    sys.exit(1)

import urllib.request

headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Accept": "application/json",
}

def fetch(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

# List services
print("=== Render Services ===")
data = fetch("https://api.render.com/v1/services?limit=20")
services = data if isinstance(data, list) else data.get("services", [])
for s in services:
    svc = s.get("service", s)
    sid = svc.get("id", "?")
    name = svc.get("name", "?")
    plan = svc.get("plan", "?")
    status = svc.get("suspended", "?")
    print(f"  id={sid} name={name} plan={plan} suspended={status}")

    if "bridge" in name.lower():
        print(f"\n  === bridge-api detail ===")
        # Check disks
        try:
            disks = fetch(f"https://api.render.com/v1/services/{sid}/disks")
            print(f"  Disks: {json.dumps(disks, indent=2)}")
        except Exception as e:
            print(f"  Disks error: {e}")

        # Check env vars (masked)
        try:
            envs = fetch(f"https://api.render.com/v1/services/{sid}/env-vars")
            for e in (envs if isinstance(envs, list) else []):
                k = e.get("envVar", {}).get("key", "?")
                if "AWS" in k or "DB" in k or "BUCKET" in k:
                    print(f"  ENV {k}={e.get('envVar', {}).get('value', '?')[:20]}...")
        except Exception as e:
            print(f"  Env vars error: {e}")
