"""
Social Auto Platform API Endpoints
===================================
구인 공고를 소셜 미디어에 자동으로 게시하는 API

Endpoints:
  POST /api/admin/social/post          — 소셜 미디어 게시
  POST /api/admin/social/account/add   — 계정 추가
  GET  /api/admin/social/platforms     — 지원하는 플랫폼 목록
  POST /api/admin/social/test-post     — 테스트 게시
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

from social_auto_platform import (
    SocialAutoOrchestrator,
    SocialPlatform,
    JobPostingRequest,
    SocialCredentialVault
)

logger = logging.getLogger("bridge.social")
router = APIRouter(prefix="/api/admin/social", tags=["social"])

# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────


class PlatformEnum(str, Enum):
    CRAIGSLIST = "craigslist"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class PostJobRequest(BaseModel):
    """소셜 미디어 게시 요청"""
    job_id: int
    job_title: str
    description: str
    company_name: str
    location: str
    salary_range: Optional[str] = None
    platforms: List[PlatformEnum] = Field(default=[PlatformEnum.CRAIGSLIST])
    media_urls: List[str] = Field(default=[])
    hashtags: List[str] = Field(default=[])


class AddAccountRequest(BaseModel):
    """소셜 미디어 계정 추가"""
    platform: PlatformEnum
    username: str
    password: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class PlatformInfo(BaseModel):
    """플랫폼 정보"""
    name: str
    value: str
    description: str
    requires_api: bool
    requires_rpa: bool
    status: str = "ready"


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────────────────────────────────────

_orchestrator: Optional[SocialAutoOrchestrator] = None


def get_orchestrator() -> SocialAutoOrchestrator:
    """Orchestrator 싱글톤 반환"""
    global _orchestrator
    if _orchestrator is None:
        try:
            _orchestrator = SocialAutoOrchestrator()
            logger.info("✅ Social Auto Orchestrator 초기화")
        except Exception as e:
            logger.error(f"Orchestrator 초기화 실패: {e}")
            raise
    return _orchestrator


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/post")
async def post_to_social(
    request_body: PostJobRequest,
    request: Request
) -> Dict[str, Any]:
    """소셜 미디어에 구인 공고 게시"""
    try:
        orchestrator = get_orchestrator()

        # 요청 객체 생성
        job_request = JobPostingRequest(
            job_id=request_body.job_id,
            job_title=request_body.job_title,
            description=request_body.description,
            company_name=request_body.company_name,
            location=request_body.location,
            salary_range=request_body.salary_range,
            platforms=[
                SocialPlatform(p) for p in request_body.platforms
            ],
            media_urls=request_body.media_urls,
            hashtags=request_body.hashtags,
        )

        # 모든 플랫폼에 게시
        results = orchestrator.post_to_all(job_request)

        logger.info(f"✅ Job {request_body.job_id} 소셜 미디어 게시 완료")
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        logger.error(f"소셜 미디어 게시 실패: {e}")
        raise HTTPException(500, f"Failed to post to social media: {str(e)}")


@router.post("/account/add")
async def add_account(
    request_body: AddAccountRequest,
    request: Request
) -> Dict[str, Any]:
    """소셜 미디어 계정 추가"""
    try:
        vault = SocialCredentialVault()
        platform = SocialPlatform(request_body.platform)

        credentials = {
            "username": request_body.username,
        }
        if request_body.password:
            credentials["password"] = request_body.password
        if request_body.api_key:
            credentials["api_key"] = request_body.api_key
        if request_body.api_secret:
            credentials["api_secret"] = request_body.api_secret

        success = vault.save_credentials(platform, credentials)

        if success:
            logger.info(f"✅ {platform.value} 계정 저장됨")
            return {
                "success": True,
                "message": f"{platform.value} 계정이 저장되었습니다."
            }
        else:
            raise HTTPException(500, "Failed to save credentials")
    except ValueError:
        raise HTTPException(400, f"Invalid platform: {request_body.platform}")
    except Exception as e:
        logger.error(f"계정 추가 실패: {e}")
        raise HTTPException(500, f"Failed to add account: {str(e)}")


@router.get("/platforms")
async def get_platforms() -> Dict[str, Any]:
    """지원하는 소셜 플랫폼 목록 반환"""
    platforms = [
        PlatformInfo(
            name="Craigslist",
            value="craigslist",
            description="Craigslist - 중고 거래 & 구직 포털",
            requires_api=False,
            requires_rpa=True,
            status="ready"
        ),
        PlatformInfo(
            name="Instagram",
            value="instagram",
            description="Instagram - 이미지 & 동영상 SNS",
            requires_api=False,
            requires_rpa=True,
            status="beta"
        ),
        PlatformInfo(
            name="TikTok",
            value="tiktok",
            description="TikTok - 쇼츠 & 라이브 플랫폼",
            requires_api=False,
            requires_rpa=True,
            status="beta"
        ),
        PlatformInfo(
            name="YouTube",
            value="youtube",
            description="YouTube - 비디오 공유 플랫폼",
            requires_api=True,
            requires_rpa=False,
            status="planning"
        ),
    ]

    return {
        "success": True,
        "platforms": [p.dict() for p in platforms]
    }


@router.post("/test-post")
async def test_post(
    request_body: PostJobRequest,
    request: Request
) -> Dict[str, Any]:
    """테스트 게시 (Craigslist만)"""
    try:
        orchestrator = get_orchestrator()

        job_request = JobPostingRequest(
            job_id=request_body.job_id,
            job_title=request_body.job_title,
            description="[TEST] " + request_body.description,
            company_name=request_body.company_name,
            location=request_body.location,
            platforms=[SocialPlatform.CRAIGSLIST],
        )

        result = orchestrator.post_to_platform(
            SocialPlatform.CRAIGSLIST,
            job_request
        )

        logger.info(f"✅ 테스트 게시 완료: Job {request_body.job_id}")
        return {
            "success": result.get("success", False),
            "data": result
        }
    except Exception as e:
        logger.error(f"테스트 게시 실패: {e}")
        raise HTTPException(500, f"Test post failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health() -> Dict[str, str]:
    """Social API 상태 확인"""
    try:
        orchestrator = get_orchestrator()
        return {"status": "healthy", "message": "Social Auto Platform is running"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
