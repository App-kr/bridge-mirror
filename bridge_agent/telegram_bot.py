"""
BRIDGE Agent Telegram Bot
==========================
폰에서 사진/텍스트로 지시 → 에이전트 실행 → 결과 회신

사용법:
  1. .env에 TELEGRAM_BOT_TOKEN 설정
  2. python -m bridge_agent.telegram_bot

텔레그램 명령:
  /start      — 시작 안내
  /help       — 명령 목록
  /agent X    — 에이전트 전환 (team-lead, security-check, feature-dev, qa-test)
  /team       — 팀리더로 전환
  /agents     — 에이전트 목록
  /model X    — 모델 변경
  /tokens     — 토큰 사용량
  /new        — 새 대화
  /status     — 서버/프로젝트 상태
  /build      — npm run build 실행
  /screenshot — 현재 localhost:3000 캡처
"""

import asyncio
import io
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
from telegram.constants import ParseMode, ChatAction

from bridge_agent.config import Config, DATA_DIR, VAULT_PATH, DB_PATH
from bridge_agent.storage.key_vault import KeyVault
from bridge_agent.storage.database import ConversationDB
from bridge_agent.llm.registry import create_provider, list_providers
from bridge_agent.agents.orchestrator import Orchestrator

# Prompt injection defense
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from prompt_guard import sanitize, scan

# ── Setup ─────────────────────────────────────────────────────

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bridge_bot")

# ── Global state ──────────────────────────────────────────────

config = Config()
vault = KeyVault(VAULT_PATH)
db = ConversationDB(DB_PATH)

# Per-user sessions: {chat_id: {orchestrator, conv_id, ...}}
sessions: dict[int, dict] = {}

# Allowed user IDs (empty = allow all)
ALLOWED_USERS: set[int] = set()
_allowed_env = os.getenv("TELEGRAM_ALLOWED_USERS", "")
if _allowed_env:
    ALLOWED_USERS = {int(x.strip()) for x in _allowed_env.split(",") if x.strip()}

PHOTOS_DIR = Path(__file__).resolve().parent.parent / "tmp_photos"
PHOTOS_DIR.mkdir(exist_ok=True)


def _check_auth(chat_id: int) -> bool:
    """Check if user is authorized."""
    if not ALLOWED_USERS:
        return True  # No restriction
    return chat_id in ALLOWED_USERS


def _get_api_key() -> str | None:
    """Get API key — try .env first, then vault."""
    # .env direct read
    env_keys = {
        "claude": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    env_name = env_keys.get(config.provider, "ANTHROPIC_API_KEY")
    key = os.getenv(env_name, "").strip()
    if key and key != "여기에_키_붙여넣기":
        return key

    # Vault fallback
    providers = list_providers()
    provider_info = providers.get(config.provider, {})
    key_name = provider_info.get("key_name", "anthropic_api_key")
    return vault.get(key_name)


def _get_session(chat_id: int) -> dict:
    """Get or create session for a chat."""
    if chat_id not in sessions:
        # Create LLM provider
        api_key = _get_api_key()

        if not api_key:
            raise ValueError(
                f"API key not configured for {config.provider}.\n"
                f"Run `python -m bridge_agent` first to set up API keys."
            )

        provider = create_provider(config.provider, api_key, config.model)

        orchestrator = Orchestrator(
            provider=provider,
            project_root=config.project_root,
        )

        conv_id = str(uuid.uuid4())
        db.create_conversation(
            conv_id, f"Telegram-{chat_id}",
            orchestrator.current_agent_name,
            config.provider, config.model,
        )

        sessions[chat_id] = {
            "orchestrator": orchestrator,
            "conv_id": conv_id,
        }

    return sessions[chat_id]


def _escape_md(text: str) -> str:
    """Minimal markdown escaping for Telegram MarkdownV2."""
    # Instead of MarkdownV2, we'll use HTML which is simpler
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


async def _send_long(update: Update, text: str):
    """Send a long message, splitting if needed (Telegram 4096 char limit)."""
    if not text:
        text = "(empty response)"

    # Try sending as-is first (plain text)
    chunks = []
    while text:
        if len(text) <= 4000:
            chunks.append(text)
            break
        # Find a good split point
        split_at = text.rfind("\n", 0, 4000)
        if split_at < 100:
            split_at = 4000
        chunks.append(text[:split_at])
        text = text[split_at:]

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk)
        except Exception:
            # If even plain text fails, truncate
            await update.message.reply_text(chunk[:3900] + "\n...(truncated)")


# ── Command Handlers ──────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        await update.message.reply_text("Unauthorized. Contact admin.")
        return

    await update.message.reply_text(
        "BRIDGE Agent Bot\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Bridge Base 프로젝트 AI 에이전트\n\n"
        "사용법:\n"
        "• 텍스트로 지시 → 에이전트가 실행\n"
        "• 사진 보내기 → AI가 분석 + 지시 수행\n"
        "• /help → 전체 명령 목록\n\n"
        f"현재: {config.provider} / {config.model}\n"
        f"에이전트: team-lead"
    )
    # Initialize session
    _get_session(update.effective_chat.id)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "BRIDGE Agent 명령어\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "/start     — 시작\n"
        "/help      — 이 도움말\n"
        "/agent X   — 에이전트 전환\n"
        "  team-lead, security-check,\n"
        "  feature-dev, qa-test\n"
        "/team      — 팀리더(위임 모드)\n"
        "/agents    — 에이전트 목록\n"
        "/model X   — 모델 변경\n"
        "/tokens    — 토큰 사용량\n"
        "/new       — 새 대화\n"
        "/status    — 서버 상태\n"
        "/build     — npm run build\n"
        "/git       — git status\n"
        "\n텍스트나 사진을 보내면 에이전트가 처리합니다."
    )


async def cmd_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return

    args = context.args
    session = _get_session(update.effective_chat.id)
    orch: Orchestrator = session["orchestrator"]

    if not args:
        await update.message.reply_text(
            f"현재 에이전트: {orch.current_agent_name}\n"
            f"사용법: /agent <name>\n"
            f"가능: team-lead, security-check, feature-dev, qa-test"
        )
        return

    name = args[0].lower()
    try:
        orch.switch_agent(name)
        await update.message.reply_text(f"에이전트 전환: {name}")
    except ValueError:
        await update.message.reply_text(
            f"Unknown: {name}\n"
            f"가능: team-lead, security-check, feature-dev, qa-test"
        )


async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    session = _get_session(update.effective_chat.id)
    session["orchestrator"].switch_agent("team-lead")
    await update.message.reply_text("팀리더 모드 (위임 가능)")


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    session = _get_session(update.effective_chat.id)
    agents = session["orchestrator"].list_agents()
    lines = ["에이전트 목록:"]
    for a in agents:
        marker = " <<<" if a["active"] else ""
        lines.append(f"  {'●' if a['active'] else '○'} {a['name']}{marker}")
    await update.message.reply_text("\n".join(lines))


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    args = context.args
    if not args:
        providers = list_providers()
        p = providers.get(config.provider, {})
        models = p.get("models", [])
        await update.message.reply_text(
            f"현재: {config.model}\n"
            f"가능: {', '.join(models)}\n"
            f"/model <name> 으로 변경"
        )
    else:
        config.model = args[0]
        # Reset session to use new model
        chat_id = update.effective_chat.id
        if chat_id in sessions:
            del sessions[chat_id]
        await update.message.reply_text(f"모델 변경: {args[0]}\n세션 초기화됨.")


async def cmd_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    session = _get_session(update.effective_chat.id)
    tin, tout = session["orchestrator"].get_total_tokens()
    usage = db.get_usage_summary()
    await update.message.reply_text(
        f"세션 토큰: {tin:,} in / {tout:,} out\n"
        f"전체 호출: {usage.get('calls', 0):,}\n"
        f"전체 토큰: {usage.get('total_in', 0):,} in / {usage.get('total_out', 0):,} out"
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return
    chat_id = update.effective_chat.id
    if chat_id in sessions:
        # Save usage
        tin, tout = sessions[chat_id]["orchestrator"].get_total_tokens()
        if tin > 0:
            db.log_usage(config.provider, config.model, tin, tout)
        del sessions[chat_id]
    await update.message.reply_text("새 대화 시작!")
    _get_session(chat_id)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    lines = ["BRIDGE 서버 상태:"]

    # Check API server
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000/api/health"],
            capture_output=True, text=True, timeout=5,
        )
        code = result.stdout.strip()
        lines.append(f"  API (8000): {'OK' if code == '200' else code}")
    except Exception:
        lines.append("  API (8000): DOWN")

    # Check frontend
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:3000"],
            capture_output=True, text=True, timeout=5,
        )
        code = result.stdout.strip()
        lines.append(f"  Frontend (3000): {'OK' if code == '200' else code}")
    except Exception:
        lines.append("  Frontend (3000): DOWN")

    # Git status
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=5,
            cwd=str(config.project_root),
        )
        changes = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0
        lines.append(f"  Git: {changes} changed files")
    except Exception:
        lines.append("  Git: error")

    await update.message.reply_text("\n".join(lines))


async def cmd_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_text("npm run build 실행 중...")
    await update.message.reply_chat_action(ChatAction.TYPING)

    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True, text=True, timeout=120,
            cwd=str(config.project_root / "web_frontend"),
        )
        if result.returncode == 0:
            await update.message.reply_text("빌드 성공!")
        else:
            error = result.stderr[-1500:] if result.stderr else result.stdout[-1500:]
            await update.message.reply_text(f"빌드 실패:\n{error}")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("빌드 타임아웃 (120초)")
    except Exception as e:
        await update.message.reply_text(f"빌드 에러: {e}")


async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update.effective_chat.id):
        return

    try:
        result = subprocess.run(
            ["git", "status"],
            capture_output=True, text=True, timeout=10,
            cwd=str(config.project_root),
        )
        await _send_long(update, result.stdout or result.stderr)
    except Exception as e:
        await update.message.reply_text(f"Git error: {e}")


# ── Message Handlers ──────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages → send to agent."""
    if not _check_auth(update.effective_chat.id):
        return

    user_text = update.message.text
    if not user_text:
        return

    # ── Prompt injection defense ──
    user_text = sanitize(user_text)
    guard = scan(user_text)
    if guard.blocked:
        logger.warning("Prompt injection blocked: %s (score=%d)", guard.matched_patterns, guard.risk_score)
        await update.message.reply_text("⚠️ 처리할 수 없는 입력입니다.")
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    try:
        session = _get_session(update.effective_chat.id)
        orch: Orchestrator = session["orchestrator"]

        # Save user message to DB
        db.add_message(session["conv_id"], "user", user_text)

        # Get agent response
        response = orch.chat(user_text)

        # Save and send
        db.add_message(session["conv_id"], "assistant", response)
        await _send_long(update, response)

    except ValueError as e:
        await update.message.reply_text(f"설정 필요: {e}")
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        await update.message.reply_text(f"에러: {str(e)[:500]}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages → save + send to agent with description."""
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    # Get the highest resolution photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # Save locally
    filename = f"tg_{update.effective_chat.id}_{photo.file_unique_id}.jpg"
    save_path = PHOTOS_DIR / filename
    await file.download_to_drive(str(save_path))

    # Get caption (user's instruction about the photo)
    caption = update.message.caption or "이 사진을 분석해줘"

    logger.info(f"Photo saved: {save_path} | Caption: {caption}")

    try:
        session = _get_session(update.effective_chat.id)
        orch: Orchestrator = session["orchestrator"]

        # Build message with photo context
        photo_msg = (
            f"[사진 수신: {save_path}]\n"
            f"사진 크기: {photo.width}x{photo.height}\n"
            f"저장 위치: {save_path}\n\n"
            f"사용자 지시: {caption}"
        )

        db.add_message(session["conv_id"], "user", photo_msg)
        response = orch.chat(photo_msg)
        db.add_message(session["conv_id"], "assistant", response)

        await _send_long(update, response)

    except Exception as e:
        logger.error(f"Photo error: {e}", exc_info=True)
        await update.message.reply_text(f"에러: {str(e)[:500]}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads (files)."""
    if not _check_auth(update.effective_chat.id):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)

    # Save to project tmp
    filename = doc.file_name or f"tg_doc_{doc.file_unique_id}"
    save_path = PHOTOS_DIR / filename
    await file.download_to_drive(str(save_path))

    caption = update.message.caption or f"이 파일을 분석해줘: {filename}"

    try:
        session = _get_session(update.effective_chat.id)
        orch: Orchestrator = session["orchestrator"]

        file_msg = (
            f"[파일 수신: {filename}]\n"
            f"크기: {doc.file_size} bytes\n"
            f"저장 위치: {save_path}\n\n"
            f"사용자 지시: {caption}"
        )

        db.add_message(session["conv_id"], "user", file_msg)
        response = orch.chat(file_msg)
        db.add_message(session["conv_id"], "assistant", response)

        await _send_long(update, response)

    except Exception as e:
        await update.message.reply_text(f"에러: {str(e)[:500]}")


# ── Main ──────────────────────────────────────────────────────

async def post_init(application: Application):
    """Set bot commands for the menu."""
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
    """Start the Telegram bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        print("  1. @BotFather에서 봇 생성")
        print("  2. .env에 TELEGRAM_BOT_TOKEN=your_token 추가")
        print("  3. 다시 실행")
        return

    # Verify API keys
    providers = list_providers()
    has_key = False
    for name, info in providers.items():
        if vault.has(info["key_name"]):
            has_key = True
            break

    if not has_key:
        print("ERROR: No API key configured.")
        print("  Run `python -m bridge_agent` first to set up API keys.")
        return

    print("=" * 50)
    print("BRIDGE Agent Telegram Bot")
    print("=" * 50)
    print(f"  Provider: {config.provider}")
    print(f"  Model: {config.model}")
    print(f"  Project: {config.project_root}")
    if ALLOWED_USERS:
        print(f"  Allowed users: {ALLOWED_USERS}")
    else:
        print(f"  Access: OPEN (set TELEGRAM_ALLOWED_USERS to restrict)")
    print()
    print("Bot starting... (Ctrl+C to stop)")
    print()

    app = Application.builder().token(token).post_init(post_init).build()

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

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
