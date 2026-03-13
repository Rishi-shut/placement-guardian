import re
import logging
from typing import List, Optional
from app.models.user import EmailMessage, PlacementEmail

logger = logging.getLogger(__name__)


DEFAULT_PLACEMENT_KEYWORDS = [
    'placement',
    'interview',
    'shortlisted',
    'hiring',
    'assessment',
    'coding test',
    'online test',
    'deadline',
    'selection',
    'offer letter',
    'recruitment',
    'campus drive',
    'job offer',
    'technical interview',
    'hr interview',
    'aptitude test',
    'selection process',
    'final round',
    'written test',
    'group discussion',
    'campus recruitment',
    'placement drive',
    'company visit',
    'pre-placement talk',
    'internship offer',
    'full time offer',
    'placement season',
    'recruitment process',
    'selection list'
]


class FilterService:
    def __init__(
        self, 
        placement_senders: List[str] = None,
        custom_keywords: List[str] = None
    ):
        self.placement_senders = [
            sender.lower().strip() 
            for sender in (placement_senders or [])
        ]
        self.custom_keywords = [
            kw.lower().strip() 
            for kw in (custom_keywords or [])
        ]
        self.all_keywords = self._get_all_keywords()

    def _get_all_keywords(self) -> List[str]:
        keywords = DEFAULT_PLACEMENT_KEYWORDS.copy()
        for kw in self.custom_keywords:
            if kw.lower() not in keywords:
                keywords.append(kw.lower())
        return keywords

    def is_placement_email(self, email: EmailMessage) -> PlacementEmail:
        matched_keywords = []
        matched_sender = None
        
        if self._check_sender_match(email):
            matched_sender = email.sender_email
        
        matched_keywords = self._check_keyword_match(email)
        
        is_placement = matched_sender is not None or len(matched_keywords) > 0
        
        return PlacementEmail(
            email=email,
            matched_keywords=matched_keywords,
            matched_sender=matched_sender,
            is_placement=is_placement
        )

    def _check_sender_match(self, email: EmailMessage) -> bool:
        sender_lower = email.sender_email.lower()
        return any(
            sender_lower == ps.lower() 
            for ps in self.placement_senders
        )

    def _check_keyword_match(self, email: EmailMessage) -> List[str]:
        matched = []
        subject_lower = email.subject.lower()
        snippet_lower = email.snippet.lower()
        
        combined_text = f"{subject_lower} {snippet_lower}"
        
        for keyword in self.all_keywords:
            if keyword in combined_text:
                matched.append(keyword)
        
        return matched

    def extract_company_and_role(self, email: EmailMessage) -> tuple[Optional[str], Optional[str]]:
        text = f"{email.subject} {email.snippet}".lower()
        
        company_patterns = [
            r'(?:from|by|company|company name|organization)\s*[:\-]?\s*([a-zA-Z0-9\s]+?)(?:\n|$)',
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s*(?:is hiring|is recruiting|has opened|has announced)',
        ]
        
        role_patterns = [
            r'(?:role|position|post|designation)\s*[:\-]?\s*([a-zA-Z0-9\s]+?)(?:\n|$)',
            r'(?:hiring for|looking for|recruiting for)\s*(?:the\s+)?(?:position of\s+)?([a-zA-Z0-9\s]+?)(?:\n|$)',
        ]
        
        company = None
        role = None
        
        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                company = match.group(1).strip()
                break
        
        for pattern in role_patterns:
            match = re.search(pattern, text)
            if match:
                role = match.group(1).strip()
                break
        
        if not company:
            company = self._extract_company_from_sender(email.sender_email)
        
        return company, role

    def _extract_company_from_sender(self, sender_email: str) -> Optional[str]:
        domain = sender_email.split('@')[-1].split('.')[0]
        if domain in ['gmail', 'yahoo', 'hotmail', 'outlook']:
            return None
        return domain.capitalize()


def create_filter_service(
    placement_senders: List[str] = None,
    custom_keywords: List[str] = None
) -> FilterService:
    return FilterService(placement_senders, custom_keywords)
