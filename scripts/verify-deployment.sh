#!/bin/bash
# 배포 전 필수 체크리스트
# 사용법: bash scripts/verify-deployment.sh

set -e

echo "=========================================="
echo "  Pre-Deployment Verification"
echo "=========================================="
echo ""

FAILED=0

# 1. 환경변수 파일 존재 확인
echo "[1/5] Checking environment files..."
if [ -f "web_frontend/.env.production" ]; then
    echo "  ✅ web_frontend/.env.production exists"
    if grep -q "NEXT_PUBLIC_API_URL" web_frontend/.env.production; then
        echo "  ✅ NEXT_PUBLIC_API_URL set in .env.production"
    else
        echo "  ❌ NEXT_PUBLIC_API_URL NOT in .env.production"
        FAILED=1
    fi
else
    echo "  ⚠️  web_frontend/.env.production missing (OK for Vercel with env vars set)"
fi
echo ""

# 2. Git 상태 확인
echo "[2/5] Checking git status..."
if git status --porcelain | grep -q "^??"; then
    echo "  ⚠️  Untracked files present (check git status)"
fi
git status --short | head -5
echo ""

# 3. 필수 파일 확인
echo "[3/5] Checking critical files..."
CRITICAL_FILES=(
    "web_frontend/package.json"
    "api_server.py"
    "master.db"
    ".bridge.key"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file MISSING"
        FAILED=1
    fi
done
echo ""

# 4. 데이터 파일 확인
echo "[4/5] Checking data files..."
DATA_FILES=(
    "web_frontend/data/board-testimonials.json"
    "web_frontend/data/board-visa.json"
    "web_frontend/data/board-korea.json"
)

for file in "${DATA_FILES[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(wc -c < "$file")
        if [ "$SIZE" -gt 100 ]; then
            echo "  ✅ $file ($(($SIZE / 1024))KB)"
        else
            echo "  ❌ $file (empty or too small)"
            FAILED=1
        fi
    else
        echo "  ❌ $file MISSING"
        FAILED=1
    fi
done
echo ""

# 5. 최근 커밋 확인
echo "[5/5] Checking recent commits..."
git log -1 --oneline
echo ""

# 최종 결과
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo "✅ All checks passed! Safe to deploy."
    exit 0
else
    echo "❌ Some checks failed. Fix issues before deploying."
    exit 1
fi
