from fastapi import APIRouter, Request, Query
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import logging

from app.config import settings
from app.services import (
    get_user_by_chat_id,
    update_user_senders,
    update_user_keywords,
    update_user_monitoring
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bot", tags=["telegram"])

telegram_app = None


async def setup_webhook():
    global telegram_app
    
    telegram_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("status", status_command))
    telegram_app.add_handler(CommandHandler("test_alarm", test_alarm_command))
    telegram_app.add_handler(CommandHandler("stop", stop_command))
    telegram_app.add_handler(CommandHandler("set_sender", set_sender_command))
    telegram_app.add_handler(CommandHandler("set_keywords", set_keywords_command))
    
    await telegram_app.initialize()
    
    webhook_url = f"{settings.BACKEND_URL}/bot/webhook"
    await telegram_app.bot.set_webhook(webhook_url)
    
    logger.info(f"Telegram webhook set to: {webhook_url}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.services.telegram_service import get_telegram_bot
    bot = await get_telegram_bot()
    await bot.start_command(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.services.telegram_service import get_telegram_bot
    bot = await get_telegram_bot()
    await bot.help_command(update, context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.services.telegram_service import get_telegram_bot
    bot = await get_telegram_bot()
    await bot.status_command(update, context)


async def test_alarm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.services.telegram_service import get_telegram_bot
    bot = await get_telegram_bot()
    await bot.test_alarm_command(update, context)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.services.telegram_service import get_telegram_bot
    bot = await get_telegram_bot()
    await bot.stop_command(update, context)


async def set_sender_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text(
            "Please provide the placement sender email.\n"
            "Example: /set_sender placement@havloc.com"
        )
        return
    
    sender = context.args[0]
    
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text(
            "Please connect your email first with /connect_email"
        )
        return
    
    if sender not in user.placement_senders:
        user.placement_senders.append(sender)
        await update_user_senders(chat_id, user.placement_senders)
    
    await update.message.reply_text(
        f"✅ Placement sender added: {sender}\n\n"
        f"You will now receive alerts for emails from this sender."
    )


async def set_keywords_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if not context.args:
        await update.message.reply_text(
            "Please provide keywords separated by spaces.\n"
            "Example: /set_keywords internship software developer"
        )
        return
    
    keywords = context.args
    
    user = await get_user_by_chat_id(chat_id)
    if not user:
        await update.message.reply_text(
            "Please connect your email first with /connect_email"
        )
        return
    
    user.custom_keywords.extend(keywords)
    unique_keywords = list(set(user.custom_keywords))
    await update_user_keywords(chat_id, unique_keywords)
    
    await update.message.reply_text(
        f"✅ Keywords updated!\n\n"
        f"Added: {', '.join(keywords)}\n"
        f"Total keywords: {len(unique_keywords)}"
    )


@router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        body = await request.json()
        update = Update.de_json(body, telegram_app.bot)
        
        await telegram_app.process_update(update)
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"ok": False}
