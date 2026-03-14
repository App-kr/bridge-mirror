# K:\BridgeCraig → Q:\Claudework\bridge base 완전 이전
$K  = "K:\BridgeCraig"
$Q  = "Q:\Claudework\bridge base"

# ── 1. 신규 폴더 생성 ──────────────────────────────────────────────
$newFolders = @(
    "$Q\data",        # Craigslist RPA DB (web app master.db와 분리)
    "$Q\images",      # 광고 이미지 (B.jpg, craig_icon.ico)
    "$Q\screenshots\craigslist"  # 게시 성공 스크린샷
)
foreach ($f in $newFolders) {
    if (-not (Test-Path $f)) {
        New-Item -ItemType Directory -Path $f -Force | Out-Null
        Write-Host "  MKDIR $f"
    } else {
        Write-Host "  EXISTS $f"
    }
}

# ── 2. 핵심 파일 복사 ──────────────────────────────────────────────
$copies = @(
    # [K: 원본] → [Q: 대상]
    @{ src="$K\craigslist_auto_rpa.py";    dst="$Q\craigslist_auto_rpa.py" },
    @{ src="$K\rpa_overlay.py";            dst="$Q\rpa_overlay.py" },
    @{ src="$K\crypto_util.py";            dst="$Q\crypto_util.py" },
    @{ src="$K\exit_popup.py";             dst="$Q\exit_popup.py" },
    @{ src="$K\.bridge.key";              dst="$Q\.bridge.key" },
    @{ src="$K\craig_icon.ico";            dst="$Q\images\craig_icon.ico" },
    @{ src="$K\images\B.jpg";             dst="$Q\images\B.jpg" },
    @{ src="$K\data\master.db";           dst="$Q\data\master.db" },   # Craigslist RPA DB
    @{ src="$K\data\master.db.bak";       dst="$Q\data\master.db.bak" },
    @{ src="$K\logs\rpa_error.log";       dst="$Q\logs\rpa_error.log" },
    @{ src="$K\logs\scheduler.log";       dst="$Q\logs\scheduler.log" },
    @{ src="$K\logs\.last_run.json";      dst="$Q\logs\.last_run.json" },
    @{ src="$K\logs\.file_hashes.json";   dst="$Q\logs\.file_hashes.json" },
    @{ src="$K\screenshots\craigslist\Job.3217_20260312_131257.png"; dst="$Q\screenshots\craigslist\Job.3217_20260312_131257.png" },
    @{ src="$K\screenshots\craigslist\Job.1882_20260312_131856.png"; dst="$Q\screenshots\craigslist\Job.1882_20260312_131856.png" },
    # scripts/ 폴더 (기존 존재)
    @{ src="$K\scheduler.py";             dst="$Q\scripts\scheduler.py" },
    @{ src="$K\backup.py";               dst="$Q\scripts\backup.py" },
    @{ src="$K\change_password.py";       dst="$Q\scripts\change_password.py" },
    @{ src="$K\install_scheduler.ps1";    dst="$Q\scripts\install_scheduler.ps1" },
    @{ src="$K\uninstall_scheduler.ps1";  dst="$Q\scripts\uninstall_scheduler.ps1" },
    @{ src="$K\launch_now.ps1";          dst="$Q\scripts\launch_now.ps1" },
    @{ src="$K\launch_scheduler.ps1";    dst="$Q\scripts\launch_scheduler.ps1" },
    @{ src="$K\run_rpa.ps1";             dst="$Q\scripts\run_rpa.ps1" },
    @{ src="$K\setup_main_pc.ps1";       dst="$Q\scripts\setup_main_pc.ps1" }
)
foreach ($c in $copies) {
    if (Test-Path $c.src) {
        Copy-Item $c.src $c.dst -Force
        $size = (Get-Item $c.dst).Length
        Write-Host "  COPY $(Split-Path $c.dst -Leaf) ($size bytes)"
    } else {
        Write-Host "  SKIP $(Split-Path $c.src -Leaf) (K: 없음)"
    }
}

# ── 3. account*.env 복사 + 경로 Q: 로 치환 ───────────────────────
foreach ($n in 1..4) {
    $src = "$K\account$n.env"
    $dst = "$Q\account$n.env"
    if (Test-Path $src) {
        $content = Get-Content $src -Raw
        # K: 또는 S: 경로를 Q: 로 교체
        $content = $content -replace 'K:\\BridgeCraig',          'Q:\Claudework\bridge base'
        $content = $content -replace 'S:\\Claudework\\BridgeCraig','Q:\Claudework\bridge base'
        $content = $content -replace 'bridge base\\data\\master\.db', 'bridge base\data\master.db'
        Set-Content -Path $dst -Value $content -Encoding UTF8
        Write-Host "  ENV  account$n.env (경로 Q: 로 업데이트)"
    }
}

# ── 4. 기본 .env 도 복사 + 경로 수정 ─────────────────────────────
$envSrc = "$K\.env"
if (Test-Path $envSrc) {
    $content = Get-Content $envSrc -Raw
    $content = $content -replace 'K:\\BridgeCraig',          'Q:\Claudework\bridge base'
    $content = $content -replace 'S:\\Claudework\\BridgeCraig','Q:\Claudework\bridge base'
    # 기존 .env 덮어쓰지 않도록 craig_ 접두어로 분리 저장
    Set-Content -Path "$Q\.env.craig" -Value $content -Encoding UTF8
    Write-Host "  ENV  .env.craig (craig 전용 env)"
}

Write-Host ""
Write-Host "=== 완료 확인 ==="
@("$Q\craigslist_auto_rpa.py","$Q\crypto_util.py","$Q\.bridge.key",
  "$Q\data\master.db","$Q\images\B.jpg",
  "$Q\account1.env","$Q\account2.env","$Q\account3.env","$Q\account4.env") | ForEach-Object {
    $name = Split-Path $_ -Leaf
    $ok   = if (Test-Path $_) { "OK $($(Get-Item $_).Length)B" } else { "MISSING" }
    Write-Host "  $name : $ok"
}
