from .gmail_service import GmailService, create_gmail_service
from .filter_service import FilterService, create_filter_service, DEFAULT_PLACEMENT_KEYWORDS
from .telegram_service import TelegramBotService, get_telegram_bot
from .firebase_service import (
    init_firebase,
    save_user,
    get_user_by_chat_id,
    get_user_by_email,
    update_user_tokens,
    get_user_tokens,
    update_user_monitoring,
    update_user_google_connected,
    update_user_last_alert,
    save_alert,
    get_user_alerts,
    update_user_senders,
    update_user_keywords
)
