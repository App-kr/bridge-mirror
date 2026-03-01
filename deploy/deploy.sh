#!/bin/bash
# ── BRIDGE 배포 자동화 스크립트 ──
# 실행: sudo bash deploy/deploy.sh

set -euo pipefail

BRIDGE_DIR="/opt/bridge"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== BRIDGE Deploy ==="
echo "Source: $REPO_DIR"
echo "Target: $BRIDGE_DIR"

# ── 1. Backend 배포 ──
echo ""
echo "── [1/5] Backend Setup ──"
cp "$REPO_DIR/api_server.py"       "$BRIDGE_DIR/backend/"
cp "$REPO_DIR/security_vault.py"   "$BRIDGE_DIR/backend/"
cp "$REPO_DIR/email_templates.py"  "$BRIDGE_DIR/backend/"
cp "$REPO_DIR/auto_pipeline_v2.py" "$BRIDGE_DIR/backend/" 2>/dev/null || true

# master.db는 최초 배포 시에만 복사 (기존 데이터 보호)
if [ ! -f "$BRIDGE_DIR/data/master.db" ]; then
  cp "$REPO_DIR/master.db" "$BRIDGE_DIR/data/" 2>/dev/null || echo "master.db not found — skip"
fi

# Python 가상환경
if [ ! -d "$BRIDGE_DIR/backend/venv" ]; then
  python3 -m venv "$BRIDGE_DIR/backend/venv"
fi
"$BRIDGE_DIR/backend/venv/bin/pip" install -q \
  fastapi uvicorn python-dotenv supabase pydantic[email] \
  cryptography pyjwt

echo "Backend files deployed."

# ── 2. Frontend 빌드 ──
echo ""
echo "── [2/5] Frontend Build ──"
cd "$REPO_DIR/web_frontend"
npm ci --production=false
npm run build

# standalone 모드 배포
rm -rf "$BRIDGE_DIR/frontend/.next"
cp -r .next/standalone/* "$BRIDGE_DIR/frontend/" 2>/dev/null || cp -r .next "$BRIDGE_DIR/frontend/"
cp -r .next/static "$BRIDGE_DIR/frontend/.next/static" 2>/dev/null || true
cp -r public "$BRIDGE_DIR/frontend/public" 2>/dev/null || true

echo "Frontend built and deployed."

# ── 3. Nginx 설정 ──
echo ""
echo "── [3/5] Nginx Config ──"
cp "$REPO_DIR/deploy/nginx-bridge.conf" /etc/nginx/sites-available/bridge
ln -sf /etc/nginx/sites-available/bridge /etc/nginx/sites-enabled/bridge
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
echo "Nginx configured."

# ── 4. Systemd 서비스 ──
echo ""
echo "── [4/5] Systemd Services ──"
cp "$REPO_DIR/deploy/bridge-api.service"      /etc/systemd/system/
cp "$REPO_DIR/deploy/bridge-frontend.service"  /etc/systemd/system/

# BRIDGE_DB_PATH를 .env에 추가 (없으면)
if ! grep -q "BRIDGE_DB_PATH" "$BRIDGE_DIR/backend/.env" 2>/dev/null; then
  echo "BRIDGE_DB_PATH=$BRIDGE_DIR/data/master.db" >> "$BRIDGE_DIR/backend/.env"
fi

systemctl daemon-reload
systemctl enable bridge-api bridge-frontend
systemctl restart bridge-api bridge-frontend

echo "Services started."

# ── 5. 권한 확인 ──
echo ""
echo "── [5/5] Permissions ──"
chown -R bridge:bridge "$BRIDGE_DIR"

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Status check:"
echo "  systemctl status bridge-api"
echo "  systemctl status bridge-frontend"
echo "  curl -s http://localhost:8000/ | python3 -m json.tool"
echo ""
echo "SSL setup (first time only):"
echo "  certbot --nginx -d bridgejob.co.kr -d www.bridgejob.co.kr"
