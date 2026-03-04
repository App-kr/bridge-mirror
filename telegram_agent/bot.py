"""
BRIDGE Agent Telegram Bot
==========================
폰에서 사진/텍스트로 지시 → 에이전트 실행 → 결과 회신

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
"""

import asyncio
import logging
import os
import subprocess
import uuid
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

    _get_session(update.effective_chat.id)
    await update.message.reply_text(
        "BRIDGE Agent Bot\n"
        "━━━━━━━━━━━━━━━━\n"
        "텍스트로 지시 → 에이전트 실행\n"
        "사진 보내기 → AI 분석 + 수행\n\n"
        f"Provider: {config.provider}\n"
        f"Model: {config.model}\n"
        f"Agent: team-lead\n\n"
        "/help 로 명령어 확인"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "명령어 목록\n"
        "━━━━━━━━━━━━━━━━\n"
        "/agent X   — 에이전트 전환\n"
        "  team-lead | security-check\n"
        "  feature-dev | qa-test\n"
        "/team      — 팀리더 모드\n"
        "/agents    — 목록 보기\n"
        "/model X   — 모델 변경\n"
        "/new       — 새 대화\n"
        "/status    — 서버 상태\n"
        "/build     — npm run build\n"
        "/git       — git status\n"
        "/tokens    — 사용량\n"
        "\n사진/파일 보내면 분석합니다."
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


# ── Message Handlers ──────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    text = update.message.text
    if not text:
        return

    logger.info(f"TEXT from {update.effective_chat.id}: {text[:50]}")
    await update.message.reply_chat_action(ChatAction.TYPING)

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
        logger.error(f"Chat error: {e}", exc_info=True)
        await update.message.reply_text(f"에러: {str(e)[:500]}")


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

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
