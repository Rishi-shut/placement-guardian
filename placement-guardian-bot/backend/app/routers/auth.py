import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest

from app.config import settings
from app.services import (
    get_user_by_chat_id,
    save_user,
    update_user_google_connected,
    update_user_monitoring,
    update_user_tokens,
    get_user_tokens
)
from app.services.gmail_service import create_gmail_service
from app.models.user import User, UserTokens
from app.services.telegram_service import get_telegram_bot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth_flows = {}


class OAuthStartRequest(BaseModel):
    chat_id: str


@router.get("/login")
async def start_oauth(chat_id: str = Query(...)):
    try:
        state = secrets.token_urlsafe(32)
        oauth_flows[state] = {
            'chat_id': chat_id,
            'created_at': datetime.utcnow()
        }
        
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=[settings.GOOGLE_OAUTH_SCOPE]
        )
        
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            state=state,
            prompt='consent'
        )
        
        logger.info(f"OAuth started for chat_id: {chat_id}")
        
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        logger.error(f"Error starting OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    try:
        flow_data = oauth_flows.pop(state, None)
        
        if not flow_data:
            logger.warning(f"Invalid state: {state}")
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        
        if (datetime.utcnow() - flow_data['created_at']).total_seconds() > 600:
            logger.warning(f"OAuth flow expired for state: {state}")
            raise HTTPException(status_code=400, detail="OAuth flow expired")
        
        chat_id = flow_data['chat_id']
        
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=[settings.GOOGLE_OAUTH_SCOPE]
        )
        
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        user_email = None
        if credentials.id_token:
            import base64
            import json
            id_token = credentials.id_token
            parts = id_token.split('.')
            if len(parts) == 3:
                payload = parts[1]
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                user_info = json.loads(base64.urlsafe_b64decode(payload))
                user_email = user_info.get('email')
        
        if not user_email:
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            user_email = profile['emailAddress']
        
        user = await get_user_by_chat_id(chat_id)
        if not user:
            user = User(telegram_chat_id=chat_id)
        
        user.email = user_email
        user.google_connected = True
        user.is_monitoring = True
        
        await save_user(user)
        
        await update_user_google_connected(chat_id, True, user_email)
        
        await update_user_tokens(
            chat_id,
            UserTokens(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=datetime.utcnow() + timedelta(hours=1),
                email=user_email
            )
        )
        
        gmail_service = create_gmail_service(credentials)
        gmail_service.setup_watch(user_email)
        
        telegram_bot = await get_telegram_bot()
        
        await telegram_bot.application.bot.send_message(
            chat_id=int(chat_id),
            text=f"""
✅ *Gmail Connected Successfully!*

Your email ({user_email}) is now connected.

🎯 The bot will now monitor for placement emails and send you alerts!

*What's next:*
1. Set your placement sender: /set_sender placement@havloc.com
2. Add custom keywords: /set_keywords <your keywords>
3. Test the alarm: /test_alarm
4. Check status: /status
"""
        )
        
        return RedirectResponse(
            url=f"https://t.me/{settings.TELEGRAM_BOT_TOKEN.split(':')[0]}?start=auth_success"
        )
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_oauth_url(chat_id: str) -> str:
    return f"{settings.BACKEND_URL}/auth/login?chat_id={chat_id}"
