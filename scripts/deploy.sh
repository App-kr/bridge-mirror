#!/bin/bash
# 배포 원클릭 스크립트
# 사용법: bash scripts/deploy.sh

set -e

echo "=========================================="
echo "  🚀 BRIDGE Deployment Script"
echo "=========================================="
echo ""

# 1단계: 환경변수 검증
echo "[Step 1/4] Verifying environment variables..."
echo ""

if [ ! -f "web_frontend/.env.production" ]; then
    echo "❌ web_frontend/.env.production not found"
    exit 1
fi

API_URL=$(grep "NEXT_PUBLIC_API_URL" web_frontend/.env.production | cut -d= -f2)
if [ -z "$API_URL" ]; then
    echo "❌ NEXT_PUBLIC_API_URL is empty"
    exit 1
fi

echo "✅ NEXT_PUBLIC_API_URL = $API_URL"
echo ""

# 2단계: 필수 파일 확인
echo "[Step 2/4] Checking critical files..."
MISSING=0

for file in master.db .bridge.key web_frontend/data/board-testimonials.json web_frontend/data/board-visa.json; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file MISSING"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "❌ Some critical files are missing"
    exit 1
fi

echo ""

# 3단계: Git 커밋 및 푸시
echo "[Step 3/4] Committing and pushing changes..."
echo ""

if [ -n "$(git status --porcelain)" ]; then
    echo "Current changes:"
    git status --short
    echo ""
    read -p "Commit message: " COMMIT_MSG
    if [ -z "$COMMIT_MSG" ]; then
        COMMIT_MSG="chore: routine deployment update"
    fi
    git add -A
    git commit -m "$COMMIT_MSG"
else
    echo "✅ No changes to commit"
fi

echo ""
echo "Pushing to main..."
git push origin main

echo ""

# 4단계: 배포 완료
echo "[Step 4/4] Deployment in progress..."
echo ""
echo "=========================================="
echo "✅ Deployment started successfully!"
echo "=========================================="
echo ""
echo "Check status:"
echo "  Vercel:  https://bridge-chi-lime.vercel.app"
echo "  Community/Visa:  https://bridge-chi-lime.vercel.app/community/visa"
echo "  Community/Testimonials:  https://bridge-chi-lime.vercel.app/community/testimonials"
echo ""
echo "Deployment typically completes in 2-5 minutes."
echo ""
