import json
import logging
from typing import Optional, List
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2.credentials import Credentials

from app.config import settings
from app.models.user import User, UserTokens, EmailMessage, Alert

logger = logging.getLogger(__name__)

_firebase_app = None
_db = None


def init_firebase():
    global _firebase_app, _db
    
    if _firebase_app is None:
        try:
            if settings.FIREBASE_PRIVATE_KEY and settings.FIREBASE_CLIENT_EMAIL:
                cred_dict = {
                    "type": "service_account",
                    "project_id": settings.FIREBASE_PROJECT_ID,
                    "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                    "client_email": settings.FIREBASE_CLIENT_EMAIL,
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
                cred = credentials.Certificate(cred_dict)
                _firebase_app = firebase_admin.initialize_app(cred)
                _db = firestore.client()
                logger.info("Firebase initialized successfully")
            else:
                logger.warning("Firebase credentials not configured")
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            raise


def get_db():
    global _db
    if _db is None:
        init_firebase()
    return _db


async def save_user(user: User) -> bool:
    try:
        db = get_db()
        user_data = user.model_dump()
        
        if user.created_at:
            user_data['created_at'] = user.created_at.isoformat()
        if user.last_alert:
            user_data['last_alert'] = user.last_alert.isoformat()
        
        db.collection('users').document(user.telegram_chat_id).set(user_data)
        logger.info(f"User saved: {user.telegram_chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        return False


async def get_user_by_chat_id(chat_id: str) -> Optional[User]:
    try:
        db = get_db()
        doc = db.collection('users').document(chat_id).get()
        
        if doc.exists:
            data = doc.to_dict()
            if data.get('created_at'):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('last_alert'):
                data['last_alert'] = datetime.fromisoformat(data['last_alert'])
            return User(**data)
        return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None


async def get_user_by_email(email: str) -> Optional[User]:
    try:
        db = get_db()
        docs = db.collection('users').where('email', '==', email).limit(1).get()
        
        for doc in docs:
            data = doc.to_dict()
            if data.get('created_at'):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('last_alert'):
                data['last_alert'] = datetime.fromisoformat(data['last_alert'])
            return User(**data)
        return None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None


async def update_user_tokens(chat_id: str, tokens: UserTokens) -> bool:
    try:
        db = get_db()
        db.collection('user_tokens').document(chat_id).set({
            'access_token': tokens.access_token,
            'refresh_token': tokens.refresh_token,
            'token_expiry': tokens.token_expiry.isoformat(),
            'email': tokens.email
        })
        return True
    except Exception as e:
        logger.error(f"Error updating user tokens: {e}")
        return False


async def get_user_tokens(chat_id: str) -> Optional[UserTokens]:
    try:
        db = get_db()
        doc = db.collection('user_tokens').document(chat_id).get()
        
        if doc.exists:
            data = doc.to_dict()
            data['token_expiry'] = datetime.fromisoformat(data['token_expiry'])
            return UserTokens(**data)
        return None
    except Exception as e:
        logger.error(f"Error getting user tokens: {e}")
        return None


async def update_user_monitoring(chat_id: str, is_monitoring: bool) -> bool:
    try:
        db = get_db()
        db.collection('users').document(chat_id).update({
            'is_monitoring': is_monitoring
        })
        return True
    except Exception as e:
        logger.error(f"Error updating user monitoring: {e}")
        return False


async def update_user_google_connected(chat_id: str, connected: bool, email: str = None) -> bool:
    try:
        db = get_db()
        update_data = {'google_connected': connected}
        if email:
            update_data['email'] = email
        db.collection('users').document(chat_id).update(update_data)
        return True
    except Exception as e:
        logger.error(f"Error updating user google connection: {e}")
        return False


async def update_user_last_alert(chat_id: str) -> bool:
    try:
        db = get_db()
        db.collection('users').document(chat_id).update({
            'last_alert': datetime.utcnow().isoformat()
        })
        return True
    except Exception as e:
        logger.error(f"Error updating last alert: {e}")
        return False


async def save_alert(alert: Alert) -> str:
    try:
        db = get_db()
        doc_ref = db.collection('alerts').document()
        alert.id = doc_ref.id
        alert_data = alert.model_dump()
        alert_data['timestamp'] = alert.timestamp.isoformat()
        doc_ref.set(alert_data)
        return doc_ref.id
    except Exception as e:
        logger.error(f"Error saving alert: {e}")
        return None


async def get_user_alerts(chat_id: str, limit: int = 10) -> List[Alert]:
    try:
        db = get_db()
        docs = db.collection('alerts').where('user_id', '==', chat_id).limit(limit).get()
        
        alerts = []
        for doc in docs:
            data = doc.to_dict()
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            alerts.append(Alert(**data))
        return alerts
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return []


async def update_user_senders(chat_id: str, senders: List[str]) -> bool:
    try:
        db = get_db()
        db.collection('users').document(chat_id).update({
            'placement_senders': senders
        })
        return True
    except Exception as e:
        logger.error(f"Error updating user senders: {e}")
        return False


async def update_user_keywords(chat_id: str, keywords: List[str]) -> bool:
    try:
        db = get_db()
        db.collection('users').document(chat_id).update({
            'custom_keywords': keywords
        })
        return True
    except Exception as e:
        logger.error(f"Error updating user keywords: {e}")
        return False
