#!/bin/bash
# Vercel 환경변수 자동 설정 스크립트
# 사용법: bash scripts/setup-vercel-env.sh

set -e

echo "=========================================="
echo "  Vercel Environment Variables Setup"
echo "=========================================="
echo ""

# 환경변수 정의
declare -A ENV_VARS=(
    ["NEXT_PUBLIC_API_URL"]="https://bridge-n7hk.onrender.com"
)

# 1. Vercel CLI 설치 확인
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

echo "Setting environment variables on Vercel..."
echo ""

# 2. 각 환경변수 설정
for key in "${!ENV_VARS[@]}"; do
    value="${ENV_VARS[$key]}"
    echo "[Setting] $key = $value"

    # Production 환경에 설정
    vercel env add "$key" --environment production << EOF
$value
EOF

    # Preview 환경에도 설정 (테스트용)
    vercel env add "$key" --environment preview << EOF
$value
EOF
done

echo ""
echo "=========================================="
echo "✅ Environment variables set successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Push to GitHub: git push origin main"
echo "2. Vercel will auto-deploy with new env vars"
echo "3. Check: https://bridge-chi-lime.vercel.app/community/visa"
