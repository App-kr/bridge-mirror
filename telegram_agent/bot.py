"""
BRIDGE Agent Telegram Bot
==========================
폰에서 사진/텍스트로 지시 → 에이전트 실행 → 결과 회신
Gmail 에러 실시간 알림 + 수신함 조회

실행: python -m telegram_agent
설정: .env에 TELEGRAM_BOT_TOKEN + ANTHROPIC_API_KEY

텔레그램 명령:
  /start      — 시작
  /help       — 명령 목록
  /agent X    — 에이전트 전환
  /team       — 팀리더 모드
  /agents     — 에이전트 목록
  /model X    — 모델 변경
  /tokens     — 토큰 사용량
  /new        — 새 대화
  /status     — 서버 상태
  /build      — npm run build
  /git        — git status
  --- Gmail 에러 모니터 ---
  /alerts     — 에러 알림 구독 ON/OFF
  /errors     — 미해결 에러 목록
  /inbox [n]  — 최근 수신 이메일 (기본 10)
  /resolve ID — 에러 해결 처리
  /check      — 즉시 Gmail 체크 (수동)
"""

import asyncio
import logging
import os
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# bridge_agent imports
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from bridge_agent.config import Config, DATA_DIR, VAULT_PATH, DB_PATH
from bridge_agent.storage.key_vault import KeyVault
from bridge_agent.storage.database import ConversationDB
from bridge_agent.llm.registry import create_provider, list_providers
from bridge_agent.agents.orchestrator import Orchestrator

# ── Setup ─────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bridge_tg")
# Reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)

config = Config()
vault = KeyVault(VAULT_PATH)
db = ConversationDB(DB_PATH)

sessions: dict[int, dict] = {}

ALLOWED_USERS: set[int] = set()
_allowed_env = os.getenv("TELEGRAM_ALLOWED_USERS", "")
if _allowed_env:
    ALLOWED_USERS = {int(x.strip()) for x in _allowed_env.split(",") if x.strip()}

PHOTOS_DIR = PROJECT_ROOT / "tmp_photos"
PHOTOS_DIR.mkdir(exist_ok=True)

# ── Gmail DB 헬퍼 ──────────────────────────────────────────────────────────────
_MAIL_DB_PATH = PROJECT_ROOT / os.getenv("BRIDGE_DB_PATH", "master.db")
if not _MAIL_DB_PATH.is_absolute():
    _MAIL_DB_PATH = PROJECT_ROOT / "master.db"


def _mail_conn() -> sqlite3.Connection:
    """master.db 연결 (inbox_emails 조회용)."""
    conn = sqlite3.connect(str(_MAIL_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 3000")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_mail_tables(conn: sqlite3.Connection):
    """inbox_emails, tg_alert_subscribers 테이블 보장."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS inbox_emails (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_message_id TEXT UNIQUE NOT NULL,
            subject          TEXT,
            from_name        TEXT,
            from_addr        TEXT,
            received_at      TEXT,
            category         TEXT DEFAULT 'general',
            is_error         INTEGER DEFAULT 0,
            error_type       TEXT,
            severity         TEXT DEFAULT 'info',
            body_preview     TEXT,
            full_body        TEXT,
            labels           TEXT,
            notified_tg      INTEGER DEFAULT 0,
            resolved         INTEGER DEFAULT 0,
            resolved_note    TEXT,
            created_at       TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tg_alert_subscribers (
            chat_id    INTEGER PRIMARY KEY,
            username   TEXT,
            added_at   TEXT NOT NULL,
            active     INTEGER DEFAULT 1
        );
    """)
    conn.commit()


# ── Helpers ───────────────────────────────────────────────────

def _check_auth(chat_id: int) -> bool:
    if not ALLOWED_USERS:
        return True
    return chat_id in ALLOWED_USERS


def _get_api_key() -> str | None:
    """Get API key — .env first, then vault."""
    env_keys = {"claude": "ANTHROPIC_API_KEY", "gemini": "GOOGLE_API_KEY"}
    env_name = env_keys.get(config.provider, "ANTHROPIC_API_KEY")
    key = os.getenv(env_name, "").strip()
    if key and not key.startswith("여기"):
        return key

    providers = list_providers()
    info = providers.get(config.provider, {})
    return vault.get(info.get("key_name", "anthropic_api_key"))


def _get_session(chat_id: int) -> dict:
    if chat_id not in sessions:
        api_key = _get_api_key()
        if not api_key:
            raise ValueError(
                "API key not set.\n"
                ".env에 ANTHROPIC_API_KEY 또는 GOOGLE_API_KEY를 추가하세요."
            )

        provider = create_provider(config.provider, api_key, config.model)
        orchestrator = Orchestrator(
            provider=provider,
            project_root=config.project_root,
        )

        conv_id = str(uuid.uuid4())
        db.create_conversation(
            conv_id, f"TG-{chat_id}",
            orchestrator.current_agent_name,
            config.provider, config.model,
        )

        sessions[chat_id] = {
            "orchestrator": orchestrator,
            "conv_id": conv_id,
        }

    return sessions[chat_id]


async def _send_long(update: Update, text: str):
    """4096자 제한 대응 — 긴 메시지 분할 전송."""
    if not text:
        text = "(empty)"

    while text:
        if len(text) <= 4000:
            await update.message.reply_text(text)
            break
        split = text.rfind("\n", 0, 4000)
        if split < 100:
            split = 4000
        await update.message.reply_text(text[:split])
        text = text[split:]


# ── Commands ──────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start from {update.effective_chat.id}")
    if not _check_auth(update.effective_chat.id):
        await update.message.reply_text("Unauthorized.")
        return

    try:
        _get_session(update.effective_chat.id)
    except Exception:
        pass
    await update.message.reply_text(
        "👋 BRIDGE Bot 시작!\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔔 이 봇이 하는 일:\n"
        "• Gmail 에러 이메일 실시간 감지 → 즉시 알림\n"
        "• git push 전 배포 승인 요청\n"
        "• 텔레그램으로 직접 배포 승인/거부/롤백\n\n"
        "📌 주요 명령어:\n"
        "/check   — Gmail 즉시 확인\n"
        "/errors  — 에러 목록\n"
        "/deploy  — 배포 상태\n"
        "/yes     — 배포 승인\n"
        "/no      — 배포 거부\n"
        "/rollback — 긴급 롤백\n\n"
        "💬 자연어로 말해도 됩니다\n"
        "\"에러 보여줘\" \"메일 체크\" \"배포 승인\" 등\n\n"
        "/help — 전체 명령어 목록"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 BRIDGE Bot 명령어\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📬 Gmail 모니터\n"
        "/check   — 지금 즉시 미읽음 메일 수 확인\n"
        "/inbox   — 최근 수신 이메일 목록 (기본10개)\n"
        "/errors  — 미해결 에러 이메일만 보기\n"
        "/resolve [ID] — 에러 해결 완료 표시\n"
        "/alerts  — 실시간 에러 알림 구독 ON/OFF\n"
        "\n🚀 배포 관리\n"
        "/deploy  — 현재 배포 요청 상태 확인\n"
        "/yes     — 대기중인 push 배포 승인 (진행됨)\n"
        "/no      — 대기중인 push 배포 거부 (차단됨)\n"
        "/rollback — 마지막 커밋 취소+재배포 (긴급복구)\n"
        "/gitlog  — 최근 커밋 기록 보기\n"
        "\n💻 서버\n"
        "/status  — API(8000)/Frontend(3000) 서버 상태\n"
        "/git     — git 변경 파일 목록\n"
        "/build   — Next.js 빌드 실행\n"
        "\n💬 자연어도 됩니다\n"
        "\"에러 보여줘\" / \"메일 체크해\" / \"롤백해\"\n"
        "\"배포 승인\" / \"상태 어때\" 등으로도 사용 가능"
    )


async def cmd_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    session = _get_session(update.effective_chat.id)
    orch: Orchestrator = session["orchestrator"]

    if not context.args:
        await update.message.reply_text(
            f"현재: {orch.current_agent_name}\n"
            "가능: team-lead, security-check, feature-dev, qa-test"
        )
        return

    name = context.args[0].lower()
    try:
        orch.switch_agent(name)
        await update.message.reply_text(f"전환: {name}")
    except ValueError:
        await update.message.reply_text(f"없는 에이전트: {name}")


async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    _get_session(update.effective_chat.id)["orchestrator"].switch_agent("team-lead")
    await update.message.reply_text("팀리더 모드")


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    agents = _get_session(update.effective_chat.id)["orchestrator"].list_agents()
    lines = ["에이전트:"]
    for a in agents:
        mark = " <<<" if a["active"] else ""
        lines.append(f"  {'●' if a['active'] else '○'} {a['name']}{mark}")
    await update.message.reply_text("\n".join(lines))


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    if not context.args:
        providers = list_providers()
        models = providers.get(config.provider, {}).get("models", [])
        await update.message.reply_text(
            f"현재: {config.model}\n가능: {', '.join(models)}"
        )
    else:
        config.model = context.args[0]
        chat_id = update.effective_chat.id
        sessions.pop(chat_id, None)
        await update.message.reply_text(f"모델: {context.args[0]} (세션 초기화)")


async def cmd_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    session = _get_session(update.effective_chat.id)
    tin, tout = session["orchestrator"].get_total_tokens()
    await update.message.reply_text(f"세션: {tin:,} in / {tout:,} out")


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    chat_id = update.effective_chat.id
    if chat_id in sessions:
        tin, tout = sessions[chat_id]["orchestrator"].get_total_tokens()
        if tin > 0:
            db.log_usage(config.provider, config.model, tin, tout)
        del sessions[chat_id]
    _get_session(chat_id)
    await update.message.reply_text("새 대화 시작!")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    await update.message.reply_chat_action(ChatAction.TYPING)

    lines = ["서버 상태:"]
    for name, port in [("API", 8000), ("Frontend", 3000)]:
        try:
            r = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 f"http://localhost:{port}"],
                capture_output=True, text=True, timeout=5,
            )
            code = r.stdout.strip()
            lines.append(f"  {name} ({port}): {'OK' if code in ('200','304') else code}")
        except Exception:
            lines.append(f"  {name} ({port}): DOWN")

    try:
        r = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=5,
            cwd=str(config.project_root),
        )
        n = len(r.stdout.strip().splitlines()) if r.stdout.strip() else 0
        lines.append(f"  Git: {n} changed files")
    except Exception:
        pass

    await update.message.reply_text("\n".join(lines))


async def cmd_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    await update.message.reply_text("npm run build 실행 중...")
    await update.message.reply_chat_action(ChatAction.TYPING)

    try:
        r = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True, text=True, timeout=120,
            cwd=str(config.project_root / "web_frontend"),
        )
        if r.returncode == 0:
            await update.message.reply_text("빌드 성공!")
        else:
            err = (r.stderr or r.stdout)[-1500:]
            await update.message.reply_text(f"빌드 실패:\n{err}")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("타임아웃 (120초)")
    except Exception as e:
        await update.message.reply_text(f"에러: {e}")


async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    try:
        r = subprocess.run(
            ["git", "status"],
            capture_output=True, text=True, timeout=10,
            cwd=str(config.project_root),
        )
        await _send_long(update, r.stdout or r.stderr)
    except Exception as e:
        await update.message.reply_text(f"에러: {e}")


# ── Gmail 에러 모니터 명령어 ───────────────────────────────────

async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """에러 알림 구독 ON/OFF."""
    if not _check_auth(update.effective_chat.id):
        return
    chat_id = update.effective_chat.id
    username = update.effective_user.username or update.effective_user.first_name or str(chat_id)
    args = context.args

    conn = _mail_conn()
    _ensure_mail_tables(conn)

    existing = conn.execute(
        "SELECT active FROM tg_alert_subscribers WHERE chat_id=?", (chat_id,)
    ).fetchone()

    if args and args[0].lower() == "off":
        if existing:
            conn.execute(
                "UPDATE tg_alert_subscribers SET active=0 WHERE chat_id=?", (chat_id,)
            )
            conn.commit()
        conn.close()
        await update.message.reply_text("🔕 에러 알림 구독 해제됨\n다시 받으려면: /alerts on")
        return

    # ON (기본)
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        conn.execute(
            "UPDATE tg_alert_subscribers SET active=1, username=? WHERE chat_id=?",
            (username, chat_id)
        )
    else:
        conn.execute(
            "INSERT INTO tg_alert_subscribers (chat_id, username, added_at, active) VALUES (?,?,?,1)",
            (chat_id, username, now)
        )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🔔 에러 알림 구독 완료!\n"
        f"Chat ID: {chat_id}\n\n"
        f"Render/Vercel 배포 실패, API 크레딧 소진 등\n"
        f"에러 이메일 도착 시 즉시 알림을 받습니다.\n\n"
        f"/alerts off  — 구독 해제"
    )


async def cmd_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """미해결 에러 이메일 목록."""
    if not _check_auth(update.effective_chat.id):
        return

    limit = 10
    if context.args:
        try:
            limit = min(int(context.args[0]), 30)
        except ValueError:
            pass

    conn = _mail_conn()
    _ensure_mail_tables(conn)
    rows = conn.execute(
        """SELECT id, error_type, severity, from_addr, subject, received_at
           FROM inbox_emails
           WHERE is_error=1 AND resolved=0
           ORDER BY created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("✅ 미해결 에러 없음\n모든 에러가 처리되었습니다.")
        return

    SEVERITY_EMOJI = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
    lines = [f"🔴 미해결 에러 {len(rows)}건:\n(처리 완료시 /resolve [ID] 입력)"]
    for r in rows:
        emoji = SEVERITY_EMOJI.get(r["severity"], "🔔")
        subject_short = (r["subject"] or "")[:40]
        lines.append(
            f"\n{emoji} ID:{r['id']} [{r['error_type']}]\n"
            f"   발신: {r['from_addr'][:35]}\n"
            f"   제목: {subject_short}\n"
            f"   → /resolve {r['id']} 로 해결 처리"
        )
    await _send_long(update, "\n".join(lines))


async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """최근 수신 이메일 목록."""
    if not _check_auth(update.effective_chat.id):
        return

    limit = 10
    if context.args:
        try:
            limit = min(int(context.args[0]), 30)
        except ValueError:
            pass

    conn = _mail_conn()
    _ensure_mail_tables(conn)
    rows = conn.execute(
        """SELECT id, category, severity, is_error, from_addr, subject, received_at
           FROM inbox_emails
           ORDER BY created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(
            "📭 수신 이메일 없음\n\n"
            "Gmail 워처가 이메일을 수집하면 여기에 표시됩니다.\n"
            "워처 상태 확인: /check"
        )
        return

    lines = [f"📬 최근 이메일 {len(rows)}건:\n(🚨=에러 이메일, 📧=일반 이메일)"]
    for r in rows:
        err_tag = "🚨" if r["is_error"] else "📧"
        subject_short = (r["subject"] or "")[:45]
        from_short = (r["from_addr"] or "")[:35]
        lines.append(f"\n{err_tag} [{r['category']}] ID:{r['id']}\n   {from_short}\n   {subject_short}")
    await _send_long(update, "\n".join(lines))


async def cmd_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """에러 해결 처리."""
    if not _check_auth(update.effective_chat.id):
        return

    if not context.args:
        await update.message.reply_text("사용법: /resolve <ID> [메모]\n예) /resolve 5 Render 재배포 완료")
        return

    try:
        error_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID는 숫자여야 합니다.")
        return

    note = " ".join(context.args[1:]) if len(context.args) > 1 else "수동 해결 처리"

    conn = _mail_conn()
    _ensure_mail_tables(conn)
    row = conn.execute(
        "SELECT id, subject, error_type FROM inbox_emails WHERE id=?", (error_id,)
    ).fetchone()

    if not row:
        conn.close()
        await update.message.reply_text(f"ID {error_id} 없음")
        return

    conn.execute(
        "UPDATE inbox_emails SET resolved=1, resolved_note=? WHERE id=?",
        (note, error_id)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ 해결 처리 완료\n"
        f"ID: {error_id}\n"
        f"제목: {row['subject']}\n"
        f"메모: {note}"
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """IMAP으로 즉시 Gmail 체크."""
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)
    await update.message.reply_text("📬 Gmail IMAP 체크 중...")

    try:
        import imaplib
        import email as _email
        import email.header as _eh

        gmail_user = os.getenv("GMAIL_USER", "")
        gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "")
        if not gmail_user or not gmail_pass:
            await update.message.reply_text(
                "❌ GMAIL_USER 또는 GMAIL_APP_PASSWORD 미설정\n.env 확인 필요"
            )
            return

        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(gmail_user, gmail_pass)
        imap.select("INBOX")
        _, data = imap.uid("search", None, "UNSEEN")
        uids = data[0].split() if data[0] else []
        imap.logout()

        conn = _mail_conn()
        _ensure_mail_tables(conn)
        total_mail = conn.execute("SELECT COUNT(*) FROM inbox_emails").fetchone()[0]
        unresolved = conn.execute(
            "SELECT COUNT(*) FROM inbox_emails WHERE is_error=1 AND resolved=0"
        ).fetchone()[0]
        conn.close()

        status_msg = "✅ 에러 없음" if unresolved == 0 else f"🚨 에러 {unresolved}건 확인 필요"
        await update.message.reply_text(
            f"📬 Gmail 체크 완료\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📥 미읽음: {len(uids)}건\n"
            f"🗄 수집된 전체: {total_mail}건\n"
            f"🚨 미해결 에러: {unresolved}건 → {status_msg}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"Gmail 워처가 실행 중이면 새 에러 이메일 도착시 자동 알림.\n\n"
            f"/errors — 에러 목록 보기\n"
            f"/inbox  — 전체 수신함 보기"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ 체크 실패: {str(e)[:300]}")


async def cmd_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """배포 승인."""
    if not _check_auth(update.effective_chat.id):
        return

    state_file = PROJECT_ROOT / "logs" / "deploy_request.json"
    if not state_file.exists():
        await update.message.reply_text("⚠️ 대기 중인 배포 요청 없음")
        return

    try:
        import json as _json
        state = _json.loads(state_file.read_text(encoding="utf-8"))
        if state.get("status") != "pending":
            await update.message.reply_text(
                f"⚠️ 이미 처리된 요청 (상태: {state.get('status')})"
            )
            return

        username = update.effective_user.username or update.effective_user.first_name or "Scarlett"
        state["status"] = "approved"
        state["approver"] = username
        state["approved_at"] = datetime.now(timezone.utc).isoformat()
        state_file.write_text(_json.dumps(state, ensure_ascii=False), encoding="utf-8")

        info = state.get("info", {})
        branch = info.get("branch", "main")
        latest = info.get("latest_msg", "")[:80]
        await update.message.reply_text(
            f"✅ <b>배포 승인!</b>\n"
            f"브랜치: {branch}\n"
            f"커밋: {latest}\n\n"
            f"➡️ git push가 진행됩니다.\n"
            f"➡️ Render(백엔드) + Vercel(프론트) 자동 배포 시작.\n"
            f"➡️ 보통 2~5분 후 사이트 반영됩니다.\n\n"
            f"⚠️ 배포 후 에러 이메일 오면 자동 알림 전송됩니다.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"에러: {e}")


async def cmd_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """배포 거부."""
    if not _check_auth(update.effective_chat.id):
        return

    state_file = PROJECT_ROOT / "logs" / "deploy_request.json"
    if not state_file.exists():
        await update.message.reply_text("⚠️ 대기 중인 배포 요청 없음")
        return

    try:
        import json as _json
        state = _json.loads(state_file.read_text(encoding="utf-8"))
        if state.get("status") != "pending":
            await update.message.reply_text(
                f"⚠️ 이미 처리된 요청 (상태: {state.get('status')})"
            )
            return

        reason = " ".join(context.args) if context.args else "거부됨"
        username = update.effective_user.username or update.effective_user.first_name or "Scarlett"
        state["status"] = "rejected"
        state["reason"] = reason
        state["rejected_by"] = username
        state["rejected_at"] = datetime.now(timezone.utc).isoformat()
        state_file.write_text(_json.dumps(state, ensure_ascii=False), encoding="utf-8")

        await update.message.reply_text(
            f"❌ <b>배포 차단됨</b>\n"
            f"사유: {reason}\n\n"
            f"➡️ git push가 중단됩니다.\n"
            f"➡️ 코드가 서버에 반영되지 않습니다.\n"
            f"➡️ 수정 후 다시 push하면 새 승인 요청이 옵니다.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"에러: {e}")


async def cmd_deploy_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """현재 배포 요청 상태 확인."""
    if not _check_auth(update.effective_chat.id):
        return

    state_file = PROJECT_ROOT / "logs" / "deploy_request.json"
    if not state_file.exists():
        await update.message.reply_text(
            "⏸ 대기 중인 배포 요청 없음\n\n"
            "git push 실행 시 자동으로 승인 요청이 전송됩니다."
        )
        return

    try:
        import json as _json
        state = _json.loads(state_file.read_text(encoding="utf-8"))
        status = state.get("status", "unknown")
        info = state.get("info", {})
        created = state.get("created_at", "")[:19].replace("T", " ")
        latest = info.get("latest_msg", "")[:60]
        cnt = info.get("commit_count", 0)
        emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(status, "❓")
        desc = {
            "pending": "승인 대기 중\n→ /yes: push 진행됨 (Render/Vercel 배포)\n→ /no: push 취소됨 (배포 안됨)",
            "approved": "이미 승인됨 — push가 진행되었습니다",
            "rejected": "거부됨 — push가 취소되었습니다",
        }.get(status, "")
        await update.message.reply_text(
            f"{emoji} 배포 상태: <b>{status}</b>\n"
            f"커밋 {cnt}개: {latest}\n"
            f"요청시각: {created}\n\n"
            f"{desc}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"에러: {e}")


async def cmd_rollback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """마지막 커밋 롤백 + 강제 push (재배포 트리거)."""
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)
    await update.message.reply_text(
        "⚠️ 롤백 실행 중...\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "git revert HEAD → 마지막 커밋을 되돌리는 새 커밋 생성\n"
        "git push → 서버에 반영 → Render/Vercel 자동 재배포"
    )

    try:
        # 현재 HEAD 확인
        r = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            capture_output=True, text=True, timeout=10,
            cwd=str(config.project_root),
        )
        log_lines = r.stdout.strip()

        # revert
        r = subprocess.run(
            ["git", "revert", "--no-edit", "HEAD"],
            capture_output=True, text=True, timeout=30,
            cwd=str(config.project_root),
        )
        if r.returncode != 0:
            await update.message.reply_text(
                f"❌ revert 실패:\n{(r.stderr or r.stdout)[-800:]}"
            )
            return

        # push
        r = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, timeout=30,
            cwd=str(config.project_root),
        )
        if r.returncode == 0:
            await update.message.reply_text(
                f"✅ 롤백 완료 — 재배포 시작됨\n\n"
                f"되돌린 커밋:\n{log_lines}\n\n"
                f"Render/Vercel에서 자동 재배포 진행 중."
            )
        else:
            await update.message.reply_text(
                f"⚠️ revert 성공, push 실패:\n{r.stderr[-500:]}"
            )
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ 타임아웃")
    except Exception as e:
        await update.message.reply_text(f"❌ 에러: {e}")


async def cmd_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """알림 최소 중요도 설정."""
    if not _check_auth(update.effective_chat.id):
        return
    chat_id = update.effective_chat.id

    LEVELS = {
        "all":      ("info",     "🟢 전체 — 모든 알림"),
        "중요":     ("warning",  "🟡 중요 이상 — 긴급+중요"),
        "warning":  ("warning",  "🟡 중요 이상 — 긴급+중요"),
        "긴급":     ("critical", "🔴 긴급만 — Render실패·결제실패·API소진"),
        "critical": ("critical", "🔴 긴급만 — Render실패·결제실패·API소진"),
    }

    conn = _mail_conn()
    _ensure_mail_tables(conn)

    # min_severity 컬럼 없으면 추가
    try:
        conn.execute("ALTER TABLE tg_alert_subscribers ADD COLUMN min_severity TEXT DEFAULT 'critical'")
        conn.commit()
    except Exception:
        pass

    if not context.args:
        row = conn.execute(
            "SELECT min_severity FROM tg_alert_subscribers WHERE chat_id=?", (chat_id,)
        ).fetchone()
        conn.close()
        cur = (row["min_severity"] if row else "critical") or "critical"
        cur_label = {"info": "🟢 전체", "warning": "🟡 중요 이상", "critical": "🔴 긴급만"}.get(cur, cur)
        await update.message.reply_text(
            f"🔔 현재 알림 설정: <b>{cur_label}</b>\n\n"
            f"변경하려면:\n"
            f"/priority all      — 🟢 전체 (push알림 포함 모든 것)\n"
            f"/priority 중요     — 🟡 긴급+중요만 (권장)\n"
            f"/priority 긴급     — 🔴 긴급만 (Render실패·결제·API소진)\n\n"
            f"중요도 기준:\n"
            f"🔴 긴급 — Render/Vercel 실패, API크레딧소진, 결제실패\n"
            f"🟡 중요 — GitHub보안, Supabase경고\n"
            f"🟢 일반 — 배포성공, 일반메일, push알림",
            parse_mode="HTML"
        )
        return

    key = context.args[0].lower()
    if key not in LEVELS:
        await update.message.reply_text("사용법: /priority all | /priority 중요 | /priority 긴급")
        conn.close()
        return

    sev, label = LEVELS[key]
    conn.execute(
        "UPDATE tg_alert_subscribers SET min_severity=? WHERE chat_id=?", (sev, chat_id)
    )
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"✅ 알림 설정 변경됨: <b>{label}</b>\n\n"
        f"이제 이 중요도 이상의 알림만 전송됩니다.",
        parse_mode="HTML"
    )


async def cmd_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """배포 게이트 ON/OFF 토글."""
    if not _check_auth(update.effective_chat.id):
        return

    import json as _json
    gate_file = PROJECT_ROOT / "logs" / "gate_state.json"
    gate_file.parent.mkdir(exist_ok=True)

    # 현재 상태 읽기
    try:
        state = _json.loads(gate_file.read_text(encoding="utf-8"))
        enabled = state.get("enabled", False)
    except Exception:
        enabled = False
        state = {}

    args = context.args

    if not args:
        # 현재 상태만 표시
        emoji = "🔴" if enabled else "🟢"
        status = "ON (승인 필요)" if enabled else "OFF (자동 통과)"
        await update.message.reply_text(
            f"🚦 배포 게이트 현재 상태: {emoji} <b>{status}</b>\n\n"
            f"{'⚠️ git push 시 텔레그램 승인 요청이 전송됩니다.' if enabled else '✅ git push 시 자동으로 통과됩니다. (알림은 옴)'}\n\n"
            f"/gate on  — 게이트 활성화 (실제 배포 전 사용)\n"
            f"/gate off — 게이트 비활성화 (Claude Code 작업 중 사용)",
            parse_mode="HTML"
        )
        return

    action = args[0].lower()
    if action == "on":
        state["enabled"] = True
        state["changed_at"] = datetime.now(timezone.utc).isoformat()
        gate_file.write_text(_json.dumps(state, ensure_ascii=False), encoding="utf-8")
        await update.message.reply_text(
            "🔴 <b>배포 게이트 ON</b>\n\n"
            "이제 git push 시 텔레그램으로 승인 요청이 전송됩니다.\n"
            "→ /yes: push 진행 (Render/Vercel 배포)\n"
            "→ /no: push 차단\n\n"
            "Claude Code 작업 완료 후 /gate off 로 다시 끄세요.",
            parse_mode="HTML"
        )
    elif action == "off":
        state["enabled"] = False
        state["changed_at"] = datetime.now(timezone.utc).isoformat()
        gate_file.write_text(_json.dumps(state, ensure_ascii=False), encoding="utf-8")
        await update.message.reply_text(
            "🟢 <b>배포 게이트 OFF</b>\n\n"
            "이제 git push 시 자동으로 통과됩니다.\n"
            "(push 알림은 계속 전송됩니다)\n\n"
            "실제 배포 전에는 /gate on 으로 켜세요.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("사용법: /gate on | /gate off | /gate")


async def cmd_gitlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """최근 커밋 로그 확인."""
    if not _check_auth(update.effective_chat.id):
        return
    try:
        n = int(context.args[0]) if context.args else 5
        n = min(n, 15)
        r = subprocess.run(
            ["git", "log", "--oneline", f"-{n}"],
            capture_output=True, text=True, timeout=10,
            cwd=str(config.project_root),
        )
        await _send_long(update, f"📋 최근 커밋 {n}개:\n\n{r.stdout or '없음'}")
    except Exception as e:
        await update.message.reply_text(f"에러: {e}")


# ── Message Handlers ──────────────────────────────────────────

async def _try_keyword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """자연어 키워드 → 명령 매핑 (Claude API 없이 동작)."""
    t = text.lower().strip()

    # 배포 승인/거부
    if any(k in t for k in ["yes", "승인", "배포 승인", "배포해", "배포하자", "배포 ok", "배포ok"]):
        await cmd_yes(update, context)
        return True
    if any(k in t for k in ["no", "거부", "배포 거부", "배포 취소", "배포 안해", "취소"]):
        await cmd_no(update, context)
        return True

    # 롤백
    if any(k in t for k in ["롤백", "rollback", "되돌려", "되돌리기", "복구"]):
        await cmd_rollback(update, context)
        return True

    # 에러
    if any(k in t for k in ["에러", "오류", "error", "에러 보여", "에러 목록"]):
        await cmd_errors(update, context)
        return True

    # 이메일/수신함
    if any(k in t for k in ["메일 체크", "이메일 체크", "메일 확인", "check", "체크"]):
        await cmd_check(update, context)
        return True
    if any(k in t for k in ["메일", "이메일", "inbox", "수신함", "받은 메일"]):
        await cmd_inbox(update, context)
        return True

    # git
    if any(k in t for k in ["git 로그", "커밋 로그", "커밋 기록", "gitlog"]):
        await cmd_gitlog(update, context)
        return True
    if any(k in t for k in ["git", "깃 상태", "변경 파일"]):
        await cmd_git(update, context)
        return True

    # 빌드
    if any(k in t for k in ["빌드", "build", "빌드해", "빌드 해줘"]):
        await cmd_build(update, context)
        return True

    # 배포 상태
    if any(k in t for k in ["배포 상태", "배포 요청", "deploy"]):
        await cmd_deploy_status(update, context)
        return True

    # 서버 상태
    if any(k in t for k in ["상태", "status", "서버", "서버 상태", "어때"]):
        await cmd_status(update, context)
        return True

    return False


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    text = update.message.text
    if not text:
        return

    logger.info(f"TEXT from {update.effective_chat.id}: {text[:50]}")
    await update.message.reply_chat_action(ChatAction.TYPING)

    # 키워드 매칭 먼저 시도 (Claude API 없이 동작)
    if await _try_keyword_cmd(update, context, text):
        return

    # Claude AI 대화 시도
    try:
        session = _get_session(update.effective_chat.id)
        orch: Orchestrator = session["orchestrator"]

        db.add_message(session["conv_id"], "user", text)
        response = orch.chat(text)
        db.add_message(session["conv_id"], "assistant", response)

        await _send_long(update, response)

    except ValueError as e:
        await update.message.reply_text(f"설정 필요:\n{e}")
    except Exception as e:
        err_str = str(e)
        logger.error(f"Chat error: {e}", exc_info=True)
        # API 크레딧 부족 시 친절한 안내
        if "credit balance" in err_str or "credits" in err_str.lower() or "402" in err_str:
            await update.message.reply_text(
                "⚠️ Anthropic API 크레딧 부족\n"
                "anthropic.com/billing 에서 충전 필요\n\n"
                "지금은 명령어로 운영 가능합니다:\n\n"
                "📬 메일\n"
                "/check — 메일 체크\n"
                "/errors — 에러 목록\n"
                "/inbox — 수신함\n\n"
                "🚀 배포\n"
                "/deploy — 배포 상태\n"
                "/yes — 배포 승인\n"
                "/no — 배포 거부\n"
                "/rollback — 긴급 롤백\n\n"
                "💻 서버\n"
                "/status — 서버 상태\n"
                "/git — git 상태\n"
                "/gitlog — 커밋 로그\n\n"
                "💬 자연어도 됩니다\n"
                "\"에러 보여줘\" / \"메일 체크\" / \"상태 어때\" 등"
            )
        else:
            await update.message.reply_text(f"❌ 에러: {str(e)[:500]}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    photo = update.message.photo[-1]  # highest res
    file = await context.bot.get_file(photo.file_id)

    filename = f"tg_{update.effective_chat.id}_{photo.file_unique_id}.jpg"
    save_path = PHOTOS_DIR / filename
    await file.download_to_drive(str(save_path))

    caption = update.message.caption or "이 사진을 분석해줘"
    logger.info(f"Photo: {save_path} | {caption}")

    try:
        session = _get_session(update.effective_chat.id)
        orch: Orchestrator = session["orchestrator"]

        msg = (
            f"[사진 수신]\n"
            f"크기: {photo.width}x{photo.height}\n"
            f"저장: {save_path}\n\n"
            f"지시: {caption}"
        )

        db.add_message(session["conv_id"], "user", msg)
        response = orch.chat(msg)
        db.add_message(session["conv_id"], "assistant", response)

        await _send_long(update, response)

    except Exception as e:
        logger.error(f"Photo error: {e}", exc_info=True)
        await update.message.reply_text(f"에러: {str(e)[:500]}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)

    filename = doc.file_name or f"tg_doc_{doc.file_unique_id}"
    save_path = PHOTOS_DIR / filename
    await file.download_to_drive(str(save_path))

    caption = update.message.caption or f"이 파일 분석: {filename}"

    try:
        session = _get_session(update.effective_chat.id)
        orch: Orchestrator = session["orchestrator"]

        msg = (
            f"[파일 수신: {filename}]\n"
            f"크기: {doc.file_size} bytes\n"
            f"저장: {save_path}\n\n"
            f"지시: {caption}"
        )

        db.add_message(session["conv_id"], "user", msg)
        response = orch.chat(msg)
        db.add_message(session["conv_id"], "assistant", response)

        await _send_long(update, response)

    except Exception as e:
        await update.message.reply_text(f"에러: {str(e)[:500]}")


# ── Main ──────────────────────────────────────────────────────

async def post_init(application: Application):
    commands = [
        BotCommand("start", "시작"),
        BotCommand("help", "도움말"),
        BotCommand("agent", "에이전트 전환"),
        BotCommand("team", "팀리더 모드"),
        BotCommand("agents", "에이전트 목록"),
        BotCommand("model", "모델 변경"),
        BotCommand("new", "새 대화"),
        BotCommand("status", "서버 상태"),
        BotCommand("build", "npm run build"),
        BotCommand("git", "git status"),
        BotCommand("tokens", "토큰 사용량"),
        BotCommand("alerts", "에러 알림 구독 ON/OFF"),
        BotCommand("errors", "미해결 에러 목록"),
        BotCommand("inbox", "최근 수신 이메일"),
        BotCommand("resolve", "에러 해결 처리"),
        BotCommand("check", "즉시 Gmail 체크"),
        BotCommand("yes", "배포 승인 ✅"),
        BotCommand("no", "배포 거부 ❌"),
        BotCommand("deploy", "배포 요청 상태 확인"),
        BotCommand("rollback", "마지막 커밋 롤백+재배포"),
        BotCommand("gitlog", "최근 커밋 로그"),
        BotCommand("priority", "알림 중요도 설정 (all/중요/긴급)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered.")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        print("  .env에 TELEGRAM_BOT_TOKEN=xxx 추가 후 재실행")
        return

    api_key = _get_api_key()
    if not api_key:
        print("ERROR: API key not configured.")
        print("  .env에 ANTHROPIC_API_KEY=xxx 또는 GOOGLE_API_KEY=xxx 추가")
        return

    print("=" * 50)
    print("BRIDGE Agent Telegram Bot")
    print("=" * 50)
    print(f"  Provider: {config.provider}")
    print(f"  Model:    {config.model}")
    print(f"  Project:  {config.project_root}")
    if ALLOWED_USERS:
        print(f"  Allowed:  {ALLOWED_USERS}")
    else:
        print(f"  Access:   OPEN (TELEGRAM_ALLOWED_USERS로 제한 가능)")
    print()
    print("Bot starting... (Ctrl+C to stop)")

    app = Application.builder().token(token).post_init(post_init).build()

    # Error handler
    async def error_handler(update, context):
        logger.error(f"Exception: {context.error}")

    app.add_error_handler(error_handler)

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("agent", cmd_agent))
    app.add_handler(CommandHandler("team", cmd_team))
    app.add_handler(CommandHandler("agents", cmd_agents))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("tokens", cmd_tokens))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("build", cmd_build))
    app.add_handler(CommandHandler("git", cmd_git))
    # Gmail 에러 모니터
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    app.add_handler(CommandHandler("errors", cmd_errors))
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CommandHandler("resolve", cmd_resolve))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("yes", cmd_yes))
    app.add_handler(CommandHandler("no", cmd_no))
    app.add_handler(CommandHandler("deploy", cmd_deploy_status))
    app.add_handler(CommandHandler("rollback", cmd_rollback))
    app.add_handler(CommandHandler("gitlog", cmd_gitlog))
    app.add_handler(CommandHandler("priority", cmd_priority))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
