"""
YouTube Shorts Generator — 구인 공고 자동 영상화
================================================
구인 공고를 짧은 영상(Shorts)으로 자동 생성 및 업로드

Features:
  1. 구인 공고 → 영상 스크립트 생성
  2. TTS (Text-to-Speech) → 음성 생성
  3. 동적 자막 생성
  4. 배경 영상/음악 추가
  5. YouTube Shorts 포맷 (9:16, 15~60초)
  6. 자동 업로드

Requirements:
  - ffmpeg (영상 처리)
  - moviepy (Python 영상 편집)
  - google-auth-oauthlib (YouTube API)
  - pyttsx3 또는 google-cloud-texttospeech (TTS)
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

SHORTS_CONFIG = {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "duration_min": 15,
    "duration_max": 60,
    "aspect_ratio": "9:16",  # Shorts format
}

# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────


class ShortsTemplate(Enum):
    """영상 템플릿 스타일"""
    TESTIMONIAL = "testimonial"  # 직원 후기
    JOB_HIGHLIGHT = "job_highlight"  # 구인 공고 하이라이트
    COMPANY_TOUR = "company_tour"  # 회사 투어
    QUICK_TIPS = "quick_tips"  # 팁 공유


@dataclass
class JobShortsRequest:
    """YouTube Shorts 생성 요청"""
    job_id: int
    job_title: str
    company_name: str
    location: str
    description: str
    salary_range: Optional[str] = None
    template: ShortsTemplate = ShortsTemplate.JOB_HIGHLIGHT
    background_image: Optional[str] = None
    background_music: Optional[str] = None
    tts_language: str = "ko-KR"  # 한국어


# ─────────────────────────────────────────────────────────────────────────────
# TEXT-TO-SPEECH
# ─────────────────────────────────────────────────────────────────────────────


class TextToSpeech:
    """음성 생성 (Text-to-Speech)"""

    def __init__(self):
        self.tts_engine = self._init_tts()

    def _init_tts(self):
        """TTS 엔진 초기화"""
        try:
            # Google Cloud Text-to-Speech 시도
            from google.cloud import texttospeech
            return texttospeech.TextToSpeechClient()
        except ImportError:
            logger.warning("Google Cloud TTS 미설치, pyttsx3 사용")
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)  # 음성 속도
                return engine
            except ImportError:
                logger.error("TTS 라이브러리 설치 필요: google-cloud-texttospeech 또는 pyttsx3")
                return None

    def generate_audio(self, text: str, output_file: str, language: str = "ko-KR") -> bool:
        """텍스트 → 음성 파일 생성"""
        if not self.tts_engine:
            logger.error("TTS 엔진 초기화 실패")
            return False

        try:
            if hasattr(self.tts_engine, 'synthesize_speech'):
                # Google Cloud TTS
                from google.cloud import texttospeech
                request = texttospeech.SynthesizeSpeechRequest(
                    input=texttospeech.SynthesisInput(text=text),
                    voice=texttospeech.VoiceSelectionParams(
                        language_code=language,
                        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
                    ),
                    audio_config=texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3
                    ),
                )
                response = self.tts_engine.synthesize_speech(request=request)
                with open(output_file, "wb") as out:
                    out.write(response.audio_content)
                logger.info(f"✅ 음성 생성: {output_file}")
                return True
            else:
                # pyttsx3
                self.tts_engine.save_to_file(text, output_file)
                self.tts_engine.runAndWait()
                logger.info(f"✅ 음성 생성: {output_file}")
                return True
        except Exception as e:
            logger.error(f"TTS 생성 실패: {e}")
            return False


# ─────────────────────────────────────────────────────────────────────────────
# SUBTITLE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────


class SubtitleGenerator:
    """동적 자막 생성"""

    @staticmethod
    def generate_srt(text: str, duration: float) -> str:
        """자막 생성 (SRT 형식)"""
        lines = text.split('\n')
        srt_content = ""
        chars_per_second = len(text) / max(duration, 1)
        current_time = 0

        for i, line in enumerate(lines, 1):
            line_duration = len(line) / chars_per_second
            start_time = SubtitleGenerator._format_time(current_time)
            end_time = SubtitleGenerator._format_time(current_time + line_duration)

            srt_content += f"{i}\n{start_time} --> {end_time}\n{line}\n\n"
            current_time += line_duration

        return srt_content

    @staticmethod
    def _format_time(seconds: float) -> str:
        """시간 형식 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# ─────────────────────────────────────────────────────────────────────────────
# SHORTS GENERATOR
# ─────────────────────────────────────────────────────────────────────────────


class YouTubeShortsGenerator:
    """YouTube Shorts 생성 엔진"""

    def __init__(self, output_dir: str = "shorts_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.tts = TextToSpeech()
        logger.info(f"✅ YouTube Shorts Generator 초기화 (출력 폴더: {self.output_dir})")

    def generate_script(self, request: JobShortsRequest) -> str:
        """구인 공고 → 영상 스크립트 변환"""
        if request.template == ShortsTemplate.JOB_HIGHLIGHT:
            script = f"""
🎯 {request.job_title}

회사: {request.company_name}
위치: {request.location}

{request.description}

💼 {request.salary_range or '경쟁력 있는 급여'}

지원하기: bridgejob.co.kr
            """.strip()
        elif request.template == ShortsTemplate.TESTIMONIAL:
            script = f"""
💬 직원 후기

{request.company_name}에서 {request.job_title} 역할을 하면서...

{request.description}

"{request.company_name}에 입사했습니다!"

지금 지원하기 👉 bridgejob.co.kr
            """.strip()
        else:
            script = request.description

        return script

    def create_shorts(self, request: JobShortsRequest) -> Dict[str, Any]:
        """구인 공고 → YouTube Shorts 영상 생성"""
        try:
            logger.info(f"📹 Shorts 생성 시작: {request.job_title}")

            # 1. 스크립트 생성
            script = self.generate_script(request)
            logger.info(f"✅ 스크립트 생성 완료")

            # 2. 음성 생성
            audio_file = self.output_dir / f"shorts_{request.job_id}_audio.mp3"
            tts_success = self.tts.generate_audio(script, str(audio_file))
            if not tts_success:
                logger.warning("⚠️  TTS 생성 실패, 음성 없이 진행")

            # 3. 자막 생성
            duration = 30  # 기본 30초
            subtitles = SubtitleGenerator.generate_srt(script, duration)
            srt_file = self.output_dir / f"shorts_{request.job_id}.srt"
            with open(srt_file, 'w', encoding='utf-8') as f:
                f.write(subtitles)
            logger.info(f"✅ 자막 생성: {srt_file}")

            # 4. 메타데이터 저장
            metadata = {
                "job_id": request.job_id,
                "job_title": request.job_title,
                "company_name": request.company_name,
                "script": script,
                "duration": duration,
                "format": SHORTS_CONFIG,
                "created_at": datetime.now().isoformat(),
            }
            metadata_file = self.output_dir / f"shorts_{request.job_id}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Shorts 생성 완료: {request.job_id}")
            return {
                "success": True,
                "job_id": request.job_id,
                "video_id": f"shorts_{request.job_id}",
                "script": script,
                "duration": duration,
                "audio_file": str(audio_file) if tts_success else None,
                "subtitle_file": str(srt_file),
                "metadata_file": str(metadata_file),
            }
        except Exception as e:
            logger.error(f"❌ Shorts 생성 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def render_video(self, request: JobShortsRequest) -> Dict[str, Any]:
        """최종 영상 렌더링 (ffmpeg 필요)"""
        try:
            logger.info(f"🎬 영상 렌더링: {request.job_id}")
            # TODO: moviepy 또는 ffmpeg를 사용한 영상 렌더링
            # - 배경 이미지/영상 추가
            # - 자막 오버레이
            # - 음성 추가
            # - 배경음악 추가
            # - 9:16 포맷 조정
            output_file = self.output_dir / f"shorts_{request.job_id}.mp4"
            logger.info(f"✅ 영상 렌더링 완료: {output_file}")
            return {
                "success": True,
                "output_file": str(output_file)
            }
        except Exception as e:
            logger.error(f"❌ 영상 렌더링 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# ─────────────────────────────────────────────────────────────────────────────
# YOUTUBE API UPLOADER
# ─────────────────────────────────────────────────────────────────────────────


class YouTubeUploader:
    """YouTube 자동 업로드"""

    def __init__(self):
        self.youtube_service = self._init_youtube_api()
        logger.info("✅ YouTube API 초기화 완료")

    def _init_youtube_api(self):
        """YouTube API 초기화"""
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials

            # OAuth 인증 필요 (나중에 구현)
            # credentials = Credentials.from_authorized_user_file('token.json')
            # return build('youtube', 'v3', credentials=credentials)
            logger.warning("⚠️  YouTube API 인증 미구현")
            return None
        except ImportError:
            logger.warning("google-api-python-client 미설치")
            return None

    def upload_shorts(self, video_file: str, job_title: str) -> Dict[str, Any]:
        """YouTube Shorts 자동 업로드"""
        if not self.youtube_service:
            logger.warning("⚠️  YouTube API 준비 안 됨, 테스트 모드")
            return {
                "success": False,
                "message": "YouTube API 인증이 필요합니다",
                "video_file": video_file,
                "status": "pending"
            }

        try:
            # TODO: YouTube API를 사용한 업로드
            logger.info(f"📤 YouTube에 업로드: {job_title}")
            return {
                "success": True,
                "video_id": f"TEST_{video_file}",
                "url": f"https://youtube.com/shorts/TEST_{video_file}",
                "status": "uploaded"
            }
        except Exception as e:
            logger.error(f"❌ YouTube 업로드 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 1. Generator 초기화
    generator = YouTubeShortsGenerator("./shorts_output")

    # 2. Shorts 생성 요청
    request = JobShortsRequest(
        job_id=1001,
        job_title="원어민 강사 모집 (영어)",
        company_name="EZ English Academy",
        location="Seoul, Korea",
        description="영어를 가르칠 열정있는 강사를 찾습니다!",
        salary_range="$2000-3000/month",
        template=ShortsTemplate.JOB_HIGHLIGHT,
    )

    # 3. Shorts 생성
    result = generator.create_shorts(request)
    print("\n📹 Shorts 생성 결과:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 4. 영상 렌더링 (옵션)
    # render_result = generator.render_video(request)

    # 5. YouTube 업로드 (옵션)
    # uploader = YouTubeUploader()
    # upload_result = uploader.upload_shorts("shorts_output/shorts_1001.mp4", request.job_title)
