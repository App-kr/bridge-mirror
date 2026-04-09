"""
tests/conftest.py — BRIDGE API 테스트 픽스처
=============================================
- Production DB/서버 절대 사용 금지
- 모든 테스트는 인메모리 SQLite + TestClient 기반
- ADMIN_API_KEY는 픽스처 내부 상수 (실제 키 노출 금지)
"""
import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

# ── 테스트 전용 환경변수 설정 (실제 키 미사용) ────────────────────────────
TEST_ADMIN_KEY = "test-admin-key-for-local-testing-only"  # gitleaks:allow
TEST_JWT_SECRET = "test-jwt-secret-local"               # gitleaks:allow
TEST_HMAC_KEY = "test-hmac-key-local"                   # gitleaks:allow

os.environ.setdefault("ADMIN_API_KEY", TEST_ADMIN_KEY)
os.environ.setdefault("JWT_SECRET", TEST_JWT_SECRET)
os.environ.setdefault("BRIDGE_HMAC_KEY", TEST_HMAC_KEY)
os.environ.setdefault("BRIDGE_SMTP_PASS", "test-smtp-pass")        # gitleaks:allow
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token") # gitleaks:allow
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")   # gitleaks:allow

# ── 테스트 DB 픽스처 ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_db_path():
    """세션 스코프 임시 SQLite DB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # 최소 스키마 생성 (api_server.py가 필요로 하는 테이블들)
    conn = sqlite3.connect(db_path)
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

    os.environ["DB_PATH"] = db_path
    yield db_path

    # 정리
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="session")
def client(test_db_path):
    """FastAPI TestClient — Production 서버 미사용."""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

    # api_server import (env 설정 후)
    import importlib
    import api_server as _api
    importlib.reload(_api)  # 환경변수 반영

    with TestClient(_api.app, raise_server_exceptions=False) as c:
        yield c


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
