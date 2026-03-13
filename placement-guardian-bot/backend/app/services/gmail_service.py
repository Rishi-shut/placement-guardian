import base64
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.models.user import EmailMessage

logger = logging.getLogger(__name__)


class GmailService:
    def __init__(self, credentials: Credentials):
        self.service = build('gmail', 'v1', credentials=credentials)
        self.credentials = credentials

    def setup_watch(self, user_email: str) -> Dict[str, Any]:
        try:
            topic_name = f"projects/{settings.GOOGLE_CLOUD_PROJECT}/topics/{settings.PUBSUB_TOPIC}"
            
            request = {
                'labelIds': ['INBOX'],
                'topicName': topic_name,
                'labelFilterBehavior': 'INCLUDE'
            }
            
            result = self.service.users().watch(userId='me', body=request).execute()
            logger.info(f"Watch setup successful for {user_email}: {result}")
            return result
        except HttpError as e:
            logger.error(f"Error setting up watch: {e}")
            raise

    def stop_watch(self) -> Dict[str, Any]:
        try:
            return self.service.users().stop(userId='me').execute()
        except HttpError as e:
            logger.error(f"Error stopping watch: {e}")
            raise

    def get_history(
        self, 
        start_history_id: str, 
        history_types: List[str] = None
    ) -> Dict[str, Any]:
        if history_types is None:
            history_types = ['messageAdded']
        
        try:
            result = self.service.users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes=history_types
            ).execute()
            return result
        except HttpError as e:
            logger.error(f"Error getting history: {e}")
            return {}

    def get_message(self, message_id: str) -> EmailMessage:
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_message(message)
        except HttpError as e:
            logger.error(f"Error getting message: {e}")
            raise

    def get_messages_batch(self, message_ids: List[str]) -> List[EmailMessage]:
        messages = []
        for msg_id in message_ids:
            try:
                msg = self.get_message(msg_id)
                messages.append(msg)
            except Exception as e:
                logger.error(f"Error fetching message {msg_id}: {e}")
        return messages

    def _parse_message(self, message: Dict[str, Any]) -> EmailMessage:
        headers = message.get('payload', {}).get('headers', [])
        
        subject = ""
        sender = ""
        sender_email = ""
        
        for header in headers:
            if header['name'].lower() == 'subject':
                subject = header['value']
            elif header['name'].lower() == 'from':
                sender = header['value']
                sender_email = self._extract_email(sender)
        
        snippet = message.get('snippet', '')
        internal_date = int(message.get('internalDate', 0))
        
        return EmailMessage(
            id=message['id'],
            thread_id=message.get('threadId', ''),
            subject=subject,
            sender=sender,
            sender_email=sender_email,
            snippet=snippet,
            timestamp=datetime.fromtimestamp(internal_date / 1000),
            is_read='UNREAD' not in message.get('labelIds', []),
            labels=message.get('labelIds', [])
        )

    def _extract_email(self, sender: str) -> str:
        import re
        match = re.search(r'<(.+?)>', sender)
        if match:
            return match.group(1).lower()
        return sender.lower()

    def get_watch_status(self) -> Optional[Dict[str, Any]]:
        try:
            result = self.service.users().getProfile(userId='me').execute()
            return result
        except HttpError as e:
            logger.error(f"Error getting watch status: {e}")
            return None


def create_gmail_service(credentials: Credentials) -> GmailService:
    return GmailService(credentials)
