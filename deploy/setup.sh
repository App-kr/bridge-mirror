#!/bin/bash
# ── BRIDGE VPS 초기 설정 스크립트 ──
# Ubuntu 24.04 기준
# 실행: sudo bash deploy/setup.sh

set -euo pipefail

echo "=== BRIDGE VPS Initial Setup ==="

# 1. 시스템 업데이트
apt update && apt upgrade -y

# 2. 필수 패키지 설치
apt install -y \
  python3 python3-pip python3-venv \
  nodejs npm \
  nginx certbot python3-certbot-nginx \
  ufw sqlite3 git curl

# 3. Node.js 20 LTS (nodesource)
if ! node -v | grep -q "v20"; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  apt install -y nodejs
fi

# 4. 방화벽 설정
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable

# 5. 앱 유저 생성
if ! id "bridge" &>/dev/null; then
  useradd -m -s /bin/bash bridge
  echo "User 'bridge' created"
fi

# 6. 디렉토리 구조
mkdir -p /opt/bridge/{backend,frontend,logs,data}
chown -R bridge:bridge /opt/bridge

echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Copy project files to /opt/bridge/"
echo "  2. Configure .env in /opt/bridge/backend/"
echo "  3. Run deploy/deploy.sh"
