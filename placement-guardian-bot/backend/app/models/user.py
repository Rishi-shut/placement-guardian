from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class User(BaseModel):
    telegram_chat_id: str
    email: Optional[str] = None
    placement_senders: List[str] = []
    custom_keywords: List[str] = []
    is_monitoring: bool = False
    created_at: Optional[datetime] = None
    last_alert: Optional[datetime] = None
    google_connected: bool = False


class UserTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_expiry: datetime
    email: str


class EmailMessage(BaseModel):
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    snippet: str
    timestamp: datetime
    is_read: bool = False
    labels: List[str] = []


class Alert(BaseModel):
    id: Optional[str] = None
    user_id: str
    email_id: str
    email_subject: str
    email_sender: str
    timestamp: datetime
    dismissed: bool = False
    company: Optional[str] = None
    role: Optional[str] = None


class PlacementEmail(BaseModel):
    email: EmailMessage
    matched_keywords: List[str] = []
    matched_sender: Optional[str] = None
    is_placement: bool = False
