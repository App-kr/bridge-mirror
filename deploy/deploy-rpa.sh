#!/bin/bash
# ── BRIDGE Craigslist RPA 서버 배포 스크립트 ──
# 서버에서 실행: sudo bash deploy/deploy-rpa.sh
#
# 사전 조건:
#   - /opt/bridge/ 디렉터리 존재
#   - /opt/bridge/backend/venv 가상환경 존재
#   - /opt/bridge/data/master.db 존재

set -euo pipefail

BRIDGE_DIR="/opt/bridge"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "  BRIDGE Craigslist RPA Deploy"
echo "=========================================="
echo "Source: $REPO_DIR"
echo "Target: $BRIDGE_DIR"
echo ""

# ── 1. Chrome 설치 (없으면) ──
echo "── [1/5] Google Chrome ──"
if command -v google-chrome-stable &>/dev/null; then
    echo "Chrome already installed: $(google-chrome-stable --version)"
else
    echo "Installing Google Chrome..."
    wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list
    apt-get update -qq
    apt-get install -y google-chrome-stable
    echo "Chrome installed: $(google-chrome-stable --version)"
fi

# ── 2. Python 패키지 설치 ──
echo ""
echo "── [2/5] Python Dependencies ──"
"$BRIDGE_DIR/backend/venv/bin/pip" install -q \
    selenium webdriver-manager python-dotenv
echo "selenium, webdriver-manager installed."

# ── 3. 파일 배포 ──
echo ""
echo "── [3/5] Deploy Files ──"

# RPA 스크립트
cp "$REPO_DIR/tools/craigslist_auto_rpa.py" "$BRIDGE_DIR/backend/"
echo "  craigslist_auto_rpa.py → $BRIDGE_DIR/backend/"

# 이미지 디렉터리
mkdir -p "$BRIDGE_DIR/images"
if [ -f "$REPO_DIR/images/B.jpg" ]; then
    cp "$REPO_DIR/images/B.jpg" "$BRIDGE_DIR/images/"
    echo "  B.jpg → $BRIDGE_DIR/images/"
else
    echo "  [WARN] images/B.jpg not found in repo — skip"
fi

# 로그 디렉터리
mkdir -p "$BRIDGE_DIR/logs"
# 스크린샷 디렉터리
mkdir -p "$BRIDGE_DIR/screenshots/craigslist"

echo "Directories created."

# ── 4. .env Craigslist 변수 확인 ──
echo ""
echo "── [4/5] Environment Variables ──"
ENV_FILE="$BRIDGE_DIR/backend/.env"

# BRIDGE_APP_DIR 추가 (없으면)
if ! grep -q "BRIDGE_APP_DIR" "$ENV_FILE" 2>/dev/null; then
    echo "" >> "$ENV_FILE"
    echo "# RPA paths" >> "$ENV_FILE"
    echo "BRIDGE_APP_DIR=$BRIDGE_DIR" >> "$ENV_FILE"
    echo "  Added BRIDGE_APP_DIR=$BRIDGE_DIR"
fi

# Craigslist 변수 존재 여부 확인
MISSING=()
for VAR in CRAIGSLIST_EMAIL CRAIGSLIST_PASSWORD CRAIGSLIST_CITY CRAIGSLIST_CONTACT; do
    if ! grep -q "$VAR" "$ENV_FILE" 2>/dev/null; then
        MISSING+=("$VAR")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "  [ACTION REQUIRED] 아래 변수를 $ENV_FILE 에 수동 추가하세요:"
    for VAR in "${MISSING[@]}"; do
        echo "    $VAR=..."
    done
    echo ""
    echo "  예시:"
    echo "    CRAIGSLIST_EMAIL=your@email.com"
    echo "    CRAIGSLIST_PASSWORD=your_password"
    echo "    CRAIGSLIST_CITY=seoul"
    echo "    CRAIGSLIST_CONTACT=bridgejobkr@gmail.com"
else
    echo "  All Craigslist env vars present."
fi

# ── 5. Cron 등록 (6시간마다) ──
echo ""
echo "── [5/5] Cron Schedule ──"
CRON_CMD="0 0,6,12,18 * * * $BRIDGE_DIR/backend/venv/bin/python $BRIDGE_DIR/backend/craigslist_auto_rpa.py --headless --limit 8 >> $BRIDGE_DIR/logs/rpa_cron.log 2>&1"

# 기존 cron에 craigslist_auto_rpa 없으면 추가
if crontab -l 2>/dev/null | grep -q "craigslist_auto_rpa"; then
    echo "  Cron entry already exists — skip"
    echo "  Current:"
    crontab -l 2>/dev/null | grep "craigslist_auto_rpa" || true
else
    # 기존 crontab 보존 + 추가
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "  Cron registered (every 6h: 00:00, 06:00, 12:00, 18:00 UTC)"
fi

# ── 권한 ──
chown -R bridge:bridge "$BRIDGE_DIR" 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Deploy Complete!"
echo "=========================================="
echo ""
echo "검증 순서:"
echo "  1. .env 변수 확인:"
echo "     cat $ENV_FILE | grep CRAIGSLIST"
echo ""
echo "  2. Dry-run 테스트 (DB 연결 + 경로 확인):"
echo "     $BRIDGE_DIR/backend/venv/bin/python $BRIDGE_DIR/backend/craigslist_auto_rpa.py --dry-run --limit 1"
echo ""
echo "  3. 실제 1건 테스트 (headless):"
echo "     $BRIDGE_DIR/backend/venv/bin/python $BRIDGE_DIR/backend/craigslist_auto_rpa.py --headless --limit 1"
echo ""
echo "  4. Cron 로그 확인:"
echo "     tail -f $BRIDGE_DIR/logs/rpa_cron.log"
echo ""
