import json, subprocess, sys
from datetime import datetime
from pathlib import Path

BASE  = Path("Q:/Claudework/bridge base")
VAULT = Path("Q:/Obsidian/Scarlett/BRIDGE")

def ts(): return datetime.now().strftime("%Y.%m.%d %H:%M")

def git(cmd):
    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()

def git_head(): return git(["git","rev-parse","--short","HEAD"])

def categorize(files):
    cats = set()
    for f in files:
        if "candidates" in f: cats.add("candidates")
        elif "employer" in f or "applications" in f: cats.add("employers")
        elif "community" in f or "board" in f: cats.add("community")
        elif "backup" in f: cats.add("backup")
        elif "api_server" in f or "render" in f: cats.add("infra")
        elif "web_frontend" in f: cats.add("web")
        elif "tools" in f: cats.add("automation")
        else: cats.add("web")
    return ", ".join(cats) or "web"

def append_worklog(task, files, commit):
    log = VAULT / "BRIDGE_작업일지.md"
    VAULT.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        log.write_text("# BRIDGE 작업일지\n\n---\n\n", encoding="utf-8")
    cat = categorize(files)
    files_md = "\n".join(f"  - {f}" for f in files[:10]) or "  - (없음)"
    entry = (
        f"### {ts()} - {task}\n"
        f"- 카테고리: {cat}\n"
        f"- 커밋: {commit}\n"
        f"- 변경:\n{files_md}\n\n"
    )
    open(log, "a", encoding="utf-8").write(entry)
    print("[일지] 완료")

def refresh_canvas():
    p = BASE / "tools" / "make_canvas.py"
    if p.exists():
        r = subprocess.run([sys.executable, "-X", "utf8", str(p)], capture_output=True, text=True)
        print("[Canvas]", "완료" if r.returncode == 0 else "실패")

def run_backup(task):
    p = BASE / "tools" / "bridge_backup.py"
    if p.exists():
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(p), "backup", task, "--type", "auto"],
            capture_output=True, text=True
        )
        print("[백업]", "완료" if r.returncode == 0 else "실패")

def run_doc_processor():
    """incoming/ 에 파일이 있으면 doc_processor batch 자동 실행"""
    incoming = BASE / "tools" / "processed_docs" / "incoming"
    if not incoming.exists():
        return
    pending = [
        f for f in incoming.iterdir()
        if f.suffix.lower() in (".docx", ".pdf")
        and not f.name.startswith("~")
        and not f.name.startswith(".")
    ]
    if not pending:
        return
    print(f"[DocProc] incoming에 {len(pending)}개 파일 발견, batch 처리 시작...")
    dp = BASE / "tools" / "doc_processor.py"
    if not dp.exists():
        print("[DocProc] doc_processor.py 없음 - skip")
        return
    r = subprocess.run(
        [sys.executable, "-X", "utf8", str(dp), "batch"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print("[DocProc] batch 완료")
        # stdout에서 주요 결과만 출력
        for line in r.stdout.splitlines():
            if any(k in line for k in ("[OK]", "[DB]", "Done!", "[SKIP]", "[ERROR]")):
                print(f"  {line.strip()}")
    else:
        print(f"[DocProc] batch 실패 (exit={r.returncode})")
        if r.stderr:
            for line in r.stderr.splitlines()[:5]:
                print(f"  {line.strip()}")

def git_commit(task):
    git(["git", "add", "-A"])
    # PAT에 workflow scope 없음 → .github/workflows/ 는 자동커밋에서 항상 제외
    # (workflow 파일은 GitHub 웹UI 또는 workflow scope PAT로 별도 push)
    wf_unstaged = git(["git", "restore", "--staged", ".github/"])
    if wf_unstaged is not None:
        # restore 실패(구버전 git) 시 reset fallback
        git(["git", "reset", "HEAD", "--", ".github/"])
    if not git(["git", "status", "--short"]):
        print("[Git] 변경없음")
        return git_head()
    print("[Git]", git(["git", "commit", "-m", f"auto: {task} [{ts()}]"]))
    return git_head()

task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "작업완료"
print(f"=== BRIDGE 자동마무리 - {task} ===")
refresh_canvas()
run_backup(task)
run_doc_processor()
files = [l.strip() for l in git(["git","diff","--name-only","HEAD"]).splitlines() if l.strip()]
commit = git_commit(task)
append_worklog(task, files, commit)
print(f"=== 완료 {ts()} / {commit} ===")
