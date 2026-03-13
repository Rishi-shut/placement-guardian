import asyncio
import logging
from typing import Optional, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


class TelegramBotService:
    def __init__(self, bot_token: str = None):
        self.token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.application: Optional[Application] = None
        self.user_handlers = {}

    async def start(self):
        self.application = Application.builder().token(self.token).build()
        
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("test_alarm", self.test_alarm_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("connect_email", self.connect_email_start)],
            states={
                1: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.connect_email_receive)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)]
        )
        self.application.add_handler(conv_handler)
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Telegram bot started successfully")

    async def stop(self):
        if self.application:
            await self.application.stop()
            logger.info("Telegram bot stopped")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        
        welcome_text = """
👋 Welcome to *Placement Guardian Bot*!

I help you never miss important placement emails from your college placement cell.

*Features:*
🔔 Real-time email monitoring
🚨 Loud alarm on placement emails
📱 Push notifications to your phone

*Commands:*
/connect_email - Connect your Gmail account
/set_sender - Set placement cell email
/set_keywords - Add custom keywords
/test_alarm - Test the alarm system
/status - Check monitoring status
/stop - Stop email monitoring
/help - Show this help message

Get started by connecting your email with /connect_email
"""
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
*Available Commands:*

/start - Start the bot
/help - Show this message
/connect_email - Connect your Gmail account
/set_sender <email> - Set placement sender (e.g., placement@havloc.com)
/set_keywords <keywords> - Add custom keywords (space separated)
/test_alarm - Test alarm trigger
/status - Check current status
/stop - Stop monitoring
"""
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown'
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from app.services.firebase_service import get_user_by_chat_id
        
        chat_id = str(update.effective_chat.id)
        user = await get_user_by_chat_id(chat_id)
        
        if not user or not user.google_connected:
            status_text = "❌ Not connected. Use /connect_email to connect your Gmail."
        else:
            status_text = f"""
*Status:*

✅ Email: {user.email}
✅ Monitoring: {'Active' if user.is_monitoring else 'Inactive'}
📧 Placement Senders: {', '.join(user.placement_senders) if user.placement_senders else 'Not set'}
🔑 Custom Keywords: {len(user.custom_keywords)} keywords configured
"""
        
        await update.message.reply_text(
            status_text,
            parse_mode='Markdown'
        )

    async def test_alarm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🔔 Trigger Alarm", callback_data="trigger_alarm")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ *Test Alarm*\n\nThis will trigger a loud alarm on your phone!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from app.services.firebase_service import update_user_monitoring
        
        chat_id = str(update.effective_chat.id)
        await update_user_monitoring(chat_id, False)
        
        await update.message.reply_text(
            "⏹️ Monitoring stopped. Use /connect_email to restart."
        )

    async def connect_email_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from app.services.firebase_service import get_user_by_chat_id
        from app.services.gmail_service import create_oauth_url
        
        chat_id = str(update.effective_chat.id)
        user = await get_user_by_chat_id(chat_id)
        
        if not user:
            user = User(telegram_chat_id=chat_id)
            await self.save_user(user)
        
        oauth_url = create_oauth_url(chat_id)
        
        await update.message.reply_text(
            f"🔗 *Connect Your Gmail*\n\n"
            f"Click the link below to authorize:\n\n"
            f"[Authorize Gmail]({oauth_url})\n\n"
            f"⚠️ We only have read access to your emails. "
            f"Your credentials are never stored.",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        return ConversationHandler.END

    async def connect_email_receive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Please use the link provided. Type /connect_email to try again."
        )
        return ConversationHandler.END

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Cancelled.")
        return ConversationHandler.END

    async def send_alert(
        self,
        chat_id: str,
        email_subject: str,
        email_sender: str,
        timestamp: datetime,
        company: str = None,
        role: str = None,
        email_id: str = None
    ):
        if not self.application:
            logger.warning("Application not initialized")
            return
        
        alarm_link = f"{settings.ALARM_DEEP_LINK_SCHEME}://trigger?email_id={email_id}"
        
        message = f"""
🚨 *PLACEMENT ALERT* 🚨

*New placement email received!*

📧 *Subject:* {email_subject}
👤 *From:* {email_sender}
⏰ *Time:* {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        if company:
            message += f"\n🏢 *Company:* {company}"
        if role:
            message += f"\n💼 *Role:* {role}"
        
        message += f"""

━━━━━━━━━━━━━━━━━━━━━

👉 [Open App - TRIGGER ALARM]({alarm_link})

_Don't miss this opportunity! Check immediately._
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📧 Open Gmail", url=f"https://mail.google.com/mail/u/0/#inbox/{email_id}"),
                InlineKeyboardButton("🔔 Trigger Alarm", callback_data=f"trigger_alarm_{email_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.application.bot.send_message(
                chat_id=int(chat_id),
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            logger.info(f"Alert sent to {chat_id}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    async def save_user(self, user: User):
        from app.services.firebase_service import save_user
        await save_user(user)


telegram_bot: Optional[TelegramBotService] = None


async def get_telegram_bot() -> TelegramBotService:
    global telegram_bot
    if telegram_bot is None:
        telegram_bot = TelegramBotService()
    return telegram_bot
