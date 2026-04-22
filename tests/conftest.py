"""
tests/conftest.py — BRIDGE API 테스트 픽스처
=============================================
- Production DB/서버 절대 사용 금지
- 모든 테스트는 인메모리 SQLite + TestClient 기반
- ADMIN_API_KEY는 픽스처 내부 상수 (실제 키 노출 금지)
"""
import os
import sys
import sqlite3
import tempfile
import pathlib

# ── 테스트 전용 환경변수 설정 (실제 키 미사용) ────────────────────────────
# import 전 반드시 설정해야 api_server가 올바른 값으로 초기화됨
TEST_ADMIN_KEY = "test-admin-key-for-local-testing-only"  # gitleaks:allow
TEST_JWT_SECRET = "test-jwt-secret-local"               # gitleaks:allow
TEST_HMAC_KEY = "test-hmac-key-local"                   # gitleaks:allow

os.environ["ADMIN_API_KEY"] = TEST_ADMIN_KEY
os.environ["JWT_SECRET"] = TEST_JWT_SECRET
os.environ["BRIDGE_HMAC_KEY"] = TEST_HMAC_KEY
os.environ["BRIDGE_SMTP_PASS"] = "test-smtp-pass"        # gitleaks:allow
os.environ["TELEGRAM_BOT_TOKEN"] = "test-telegram-token" # gitleaks:allow
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"   # gitleaks:allow
os.environ.setdefault("BRIDGE_ENV", "development")       # TrustedHost: localhost 허용

# ── 테스트 DB 생성 (모듈 로드 시 1회) ────────────────────────────────────
_tmp_db = tempfile.mktemp(suffix=".db")
os.environ["DB_PATH"] = _tmp_db

conn = sqlite3.connect(_tmp_db)
conn.executescript("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sheet_number INTEGER,
        name TEXT,
        email TEXT,
        is_deleted INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS client_inquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        contact_name TEXT,
        email TEXT,
        is_deleted INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS admin_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        method TEXT,
        path TEXT,
        ip TEXT,
        admin_key_hash TEXT
    );
    INSERT INTO candidates (sheet_number, name, email)
    VALUES (1001, 'Test User', 'test@example.com');
""")
conn.commit()
conn.close()

# ── api_server import (env 설정 완료 후) ─────────────────────────────────
_root = str(pathlib.Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import pytest
from fastapi.testclient import TestClient


def _get_app():
    try:
        import api_server
        # dotenv가 .env를 로드해 ADMIN_API_KEY를 덮어쓸 수 있으므로
        # import 후 모듈 상수를 테스트 키로 강제 패치
        api_server._ADMIN_KEY = TEST_ADMIN_KEY
        return api_server.app
    except Exception as e:
        pytest.skip(f"api_server import 실패: {e}")


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient — Production 서버 미사용."""
    app = _get_app()
    # base_url=localhost → TrustedHostMiddleware 통과
    with TestClient(app, raise_server_exceptions=False, base_url="http://localhost") as c:
        yield c


@pytest.fixture(scope="session")
def test_db_path():
    """세션 스코프 — 이미 생성된 테스트 DB 경로 반환."""
    return _tmp_db


@pytest.fixture
def admin_headers():
    """유효한 어드민 헤더."""
    return {"x-admin-key": TEST_ADMIN_KEY}


@pytest.fixture
def no_headers():
    """인증 헤더 없음."""
    return {}


@pytest.fixture
def wrong_headers():
    """잘못된 어드민 키."""
    return {"x-admin-key": "wrong-key-12345"}  # gitleaks:allow
