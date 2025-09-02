from dataclasses import dataclass, field
from typing import List, Dict, Optional

DEFAULT_ENTITIES = [
    "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD",
    "US_SSN", "LOCATION", "IBAN_CODE", "DOMAIN_NAME", "IP_ADDRESS",
    "DATE_TIME", "CRYPTO", "NRP"
]

@dataclass
class RedactionConfig:
    entities: List[str] = field(default_factory=lambda: DEFAULT_ENTITIES.copy())
    custom_patterns: Dict[str, str] = field(default_factory=dict)
    confidence_threshold: float = 0.5
    placeholder_text: Optional[str] = "[REDACTED]"
    use_ocr_for_scans: bool = False
    remove_header_logo_px: int = 0
