import json
import logging
import base64
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.services import (
    get_user_by_chat_id,
    get_user_by_email,
    get_user_tokens,
    update_user_google_connected,
    update_user_monitoring,
    update_user_tokens,
    save_user,
    get_telegram_bot
)
from app.services.gmail_service import GmailService, create_gmail_service
from app.services.filter_service import create_filter_service
from app.models.user import User, UserTokens, EmailMessage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


class PubSubMessage(BaseModel):
    data: Optional[str] = None


@router.post("/gmail")
async def gmail_webhook(request: Request):
    try:
        envelope = await request.json()
        logger.info(f"Received webhook: {envelope}")
        
        if not envelope or 'message' not in envelope:
            logger.warning("Invalid webhook payload")
            return {"status": "invalid payload"}
        
        message_data = envelope.get('message', {})
        
        if not message_data.get('data'):
            logger.warning("No message data in webhook")
            return {"status": "no data"}
        
        email_address = envelope.get('emailAddress')
        history_id = message_data.get('historyId')
        
        logger.info(f"New email event - historyId: {history_id}, email: {email_address}")
        
        if email_address:
            await process_new_email(email_address, history_id)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_new_email(email_address: str, history_id: str):
    try:
        user = await get_user_by_email(email_address)
        
        if not user or not user.is_monitoring:
            logger.info(f"No active monitoring for {email_address}")
            return
        
        user_tokens = await get_user_tokens(user.telegram_chat_id)
        
        if not user_tokens:
            logger.warning(f"No tokens found for user {email_address}")
            return
        
        credentials = Credentials(
            token=user_tokens.access_token,
            refresh_token=user_tokens.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        if credentials.expired:
            credentials.refresh(GoogleRequest())
            await update_user_tokens(
                user.telegram_chat_id,
                UserTokens(
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expiry=credentials.expiry,
                    email=email_address
                )
            )
        
        gmail_service = create_gmail_service(credentials)
        
        history = gmail_service.get_history(history_id)
        
        if 'history' not in history:
            return
        
        messages_added = history['history']
        
        for history_item in messages_added:
            if 'messagesAdded' not in history_item:
                continue
            
            for msg in history_item['messagesAdded']:
                message_id = msg['id']
                
                try:
                    email = gmail_service.get_message(message_id)
                    
                    filter_service = create_filter_service(
                        placement_senders=user.placement_senders,
                        custom_keywords=user.custom_keywords
                    )
                    
                    placement_result = filter_service.is_placement_email(email)
                    
                    if placement_result.is_placement:
                        logger.info(f"Placement email detected: {email.subject}")
                        
                        company, role = filter_service.extract_company_and_role(email)
                        
                        telegram_bot = await get_telegram_bot()
                        await telegram_bot.send_alert(
                            chat_id=user.telegram_chat_id,
                            email_subject=email.subject,
                            email_sender=email.sender,
                            timestamp=email.timestamp,
                            company=company,
                            role=role,
                            email_id=email.id
                        )
                        
                except Exception as e:
                    logger.error(f"Error processing message {message_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error processing new email: {e}")


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "placement-guardian-bot"}
