from pathlib import Path
BASE = Path(r"Q:\Claudework\bridge base")
for i in range(1, 5):
    f = BASE / f"account{i}.env"
    txt = f.read_text(encoding="utf-8")
    fixed = txt.replace("CRAIGSLIST_PASSWORD=ENC:ENC:", "CRAIGSLIST_PASSWORD=ENC:")
    f.write_text(fixed, encoding="utf-8")
    line = [l for l in fixed.splitlines() if "CRAIGSLIST_PASSWORD" in l][0]
    print(f"account{i}: {line[:55]}")
