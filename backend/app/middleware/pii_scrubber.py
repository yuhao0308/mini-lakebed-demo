"""
T05: PII Scrubber Middleware

PII redaction middleware for LLM context protection.
Per tasks/T05_governance.md and 03_implementation_dummy_data_plan.md §5.3

Masks sensitive fields before passing to LLM:
- SSN → ***-**-6789
- DOB → 1985-04-01 (preserves year/month for age check)
- Email → j****@example.com
- Account numbers → masked
"""

import re
import hashlib
import json
import copy
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field

from app.models.authorization import ClearanceLevel


@dataclass
class ScrubbingResult:
    """Result of PII scrubbing with audit trail."""
    original_hash: str  # Hash of original for audit
    scrubbed_data: Dict[str, Any]
    fields_scrubbed: List[str] = field(default_factory=list)
    scrubbing_applied: bool = False


class PIIScrubber:
    """
    PII redaction middleware for LLM context.

    Per spec §5.3: Mask sensitive fields before passing to LLM.

    Scrubbing levels:
    - HIGH clearance: Full access (no scrubbing)
    - MEDIUM clearance: SSN masked, DOB masked
    - LOW clearance: All PII masked
    """

    # Regex patterns for PII detection
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    SSN_FULL_PATTERN = re.compile(r'\b\d{9}\b')
    ACCOUNT_PATTERN = re.compile(r'\b\d{10,16}\b')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    DOB_PATTERN = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')

    # Fields that commonly contain PII
    PII_FIELD_NAMES = {
        'ssn', 'social_security', 'social_security_number', 'ssn_token',
        'dob', 'date_of_birth', 'birth_date', 'birthday',
        'email', 'email_address',
        'phone', 'phone_number', 'mobile', 'cell',
        'account_number', 'bank_account', 'routing_number',
        'drivers_license', 'license_number', 'dl_number',
        'passport', 'passport_number',
        'address', 'street_address', 'home_address'
    }

    def scrub_ssn(self, ssn: str) -> str:
        """
        Mask SSN preserving last 4 digits.

        "123-45-6789" → "***-**-6789"
        "123456789" → "***-**-6789"

        Per spec §5.3: SSN → `***-**-6789`
        """
        if not ssn:
            return ssn

        # Handle formatted SSN
        if '-' in ssn:
            parts = ssn.split('-')
            if len(parts) == 3 and len(parts[2]) == 4:
                return f"***-**-{parts[2]}"

        # Handle unformatted 9-digit SSN
        if len(ssn) == 9 and ssn.isdigit():
            return f"***-**-{ssn[-4:]}"

        # Return last 4 digits if we can find them
        digits = ''.join(c for c in ssn if c.isdigit())
        if len(digits) >= 4:
            return f"***-**-{digits[-4:]}"

        return "***-**-****"

    def scrub_dob(self, dob: str) -> str:
        """
        Mask DOB preserving year/month for age calculation.

        "1985-04-12" → "1985-04-01"

        Per spec: Allows AI to check "Is applicant over 18?"
        without exposing exact birthday.
        """
        if not dob:
            return dob

        # Handle YYYY-MM-DD format
        parts = dob.split("-")
        if len(parts) == 3:
            return f"{parts[0]}-{parts[1]}-01"

        # Handle MM/DD/YYYY format
        if "/" in dob:
            parts = dob.split("/")
            if len(parts) == 3:
                # Assume MM/DD/YYYY
                return f"{parts[2]}-{parts[0]}-01"

        return dob

    def scrub_email(self, email: str) -> str:
        """
        Mask email preserving domain.

        "john.doe@example.com" → "j****@example.com"
        "a@example.com" → "****@example.com"

        Per spec §5.3: email masked
        """
        if not email or "@" not in email:
            return email

        local, domain = email.split("@", 1)
        if len(local) > 1:
            return f"{local[0]}****@{domain}"
        return f"****@{domain}"

    def scrub_phone(self, phone: str) -> str:
        """
        Mask phone number preserving last 4 digits.

        "555-123-4567" → "***-***-4567"
        """
        if not phone:
            return phone

        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) >= 4:
            return f"***-***-{digits[-4:]}"
        return "***-***-****"

    def scrub_account_number(self, account: str) -> str:
        """
        Mask account number preserving last 4 digits.

        "1234567890123456" → "************3456"
        """
        if not account:
            return account

        digits = ''.join(c for c in str(account) if c.isdigit())
        if len(digits) >= 4:
            masked_len = len(digits) - 4
            return "*" * masked_len + digits[-4:]
        return "****"

    def scrub_address(self, address: str) -> str:
        """
        Mask street address preserving city/state.

        "123 Main St, Springfield, IL" → "*** Main St, Springfield, IL"
        """
        if not address:
            return address

        # Simple approach: mask numbers at start
        parts = address.split(',')
        if parts:
            # Mask the street number in first part
            first_part = parts[0]
            words = first_part.split()
            if words and words[0].isdigit():
                words[0] = "***"
            parts[0] = ' '.join(words)

        return ','.join(parts)

    def _hash_data(self, data: Any) -> str:
        """Generate SHA-256 hash of data for audit trail."""
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def scrub_text(self, text: str) -> tuple[str, List[str]]:
        """
        Scrub PII patterns from free-form text.

        Returns tuple of (scrubbed_text, list_of_scrubbed_fields)
        """
        if not text or not isinstance(text, str):
            return text, []

        scrubbed = text
        fields_scrubbed = []

        # Scrub SSNs
        if self.SSN_PATTERN.search(scrubbed):
            scrubbed = self.SSN_PATTERN.sub(lambda m: self.scrub_ssn(m.group()), scrubbed)
            fields_scrubbed.append("ssn_pattern")

        if self.SSN_FULL_PATTERN.search(scrubbed):
            scrubbed = self.SSN_FULL_PATTERN.sub(lambda m: self.scrub_ssn(m.group()), scrubbed)
            fields_scrubbed.append("ssn_full_pattern")

        # Scrub account numbers (long digit sequences)
        if self.ACCOUNT_PATTERN.search(scrubbed):
            scrubbed = self.ACCOUNT_PATTERN.sub(
                lambda m: self.scrub_account_number(m.group()), scrubbed
            )
            fields_scrubbed.append("account_pattern")

        return scrubbed, fields_scrubbed

    def scrub_dict(
        self,
        data: Dict[str, Any],
        clearance_level: ClearanceLevel = ClearanceLevel.LOW,
        path: str = ""
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Recursively scrub PII from a dictionary.

        Args:
            data: Dictionary to scrub
            clearance_level: User's clearance level
            path: Current path in nested structure (for field tracking)

        Returns:
            Tuple of (scrubbed_dict, list_of_scrubbed_field_paths)
        """
        if clearance_level == ClearanceLevel.HIGH:
            return data, []

        result = {}
        fields_scrubbed = []

        for key, value in data.items():
            key_lower = key.lower()
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, dict):
                # Recursively scrub nested dicts
                scrubbed_value, nested_fields = self.scrub_dict(
                    value, clearance_level, current_path
                )
                result[key] = scrubbed_value
                fields_scrubbed.extend(nested_fields)

            elif isinstance(value, list):
                # Scrub each item in list
                scrubbed_list = []
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        scrubbed_item, nested_fields = self.scrub_dict(
                            item, clearance_level, f"{current_path}[{i}]"
                        )
                        scrubbed_list.append(scrubbed_item)
                        fields_scrubbed.extend(nested_fields)
                    elif isinstance(item, str):
                        scrubbed_item, _ = self.scrub_text(item)
                        scrubbed_list.append(scrubbed_item)
                    else:
                        scrubbed_list.append(item)
                result[key] = scrubbed_list

            elif isinstance(value, str):
                # Check if this is a known PII field
                if key_lower in self.PII_FIELD_NAMES or any(
                    pii_name in key_lower for pii_name in ['ssn', 'social', 'account']
                ):
                    # Apply specific scrubbing based on field type
                    if 'ssn' in key_lower or 'social' in key_lower:
                        result[key] = self.scrub_ssn(value)
                        fields_scrubbed.append(current_path)
                    elif 'dob' in key_lower or 'birth' in key_lower:
                        if clearance_level == ClearanceLevel.LOW:
                            result[key] = self.scrub_dob(value)
                            fields_scrubbed.append(current_path)
                        else:
                            result[key] = self.scrub_dob(value)
                            fields_scrubbed.append(current_path)
                    elif 'email' in key_lower:
                        if clearance_level == ClearanceLevel.LOW:
                            result[key] = self.scrub_email(value)
                            fields_scrubbed.append(current_path)
                        else:
                            result[key] = value
                    elif 'phone' in key_lower or 'mobile' in key_lower:
                        if clearance_level == ClearanceLevel.LOW:
                            result[key] = self.scrub_phone(value)
                            fields_scrubbed.append(current_path)
                        else:
                            result[key] = value
                    elif 'account' in key_lower:
                        result[key] = self.scrub_account_number(value)
                        fields_scrubbed.append(current_path)
                    elif 'address' in key_lower:
                        if clearance_level == ClearanceLevel.LOW:
                            result[key] = self.scrub_address(value)
                            fields_scrubbed.append(current_path)
                        else:
                            result[key] = value
                    else:
                        result[key] = value
                else:
                    # Scrub any PII patterns in the text
                    scrubbed_value, text_fields = self.scrub_text(value)
                    result[key] = scrubbed_value
                    if text_fields:
                        fields_scrubbed.append(current_path)
            else:
                # Non-string, non-dict, non-list values pass through
                result[key] = value

        return result, fields_scrubbed

    def scrub_customer_profile(
        self,
        profile: Dict[str, Any],
        clearance_level: Union[str, ClearanceLevel]
    ) -> ScrubbingResult:
        """
        Scrub customer profile based on clearance level.

        High clearance: Full access (no scrubbing)
        Medium clearance: SSN masked, DOB masked
        Low clearance: All PII masked

        Args:
            profile: Customer profile dictionary
            clearance_level: User's clearance level

        Returns:
            ScrubbingResult with scrubbed data and audit info
        """
        # Normalize clearance level
        if isinstance(clearance_level, str):
            clearance_level = ClearanceLevel(clearance_level.lower())

        # Hash original for audit
        original_hash = self._hash_data(profile)

        # Make a deep copy to avoid modifying original
        data = copy.deepcopy(profile)

        if clearance_level == ClearanceLevel.HIGH:
            return ScrubbingResult(
                original_hash=original_hash,
                scrubbed_data=data,
                fields_scrubbed=[],
                scrubbing_applied=False
            )

        scrubbed_data, fields_scrubbed = self.scrub_dict(data, clearance_level)

        return ScrubbingResult(
            original_hash=original_hash,
            scrubbed_data=scrubbed_data,
            fields_scrubbed=fields_scrubbed,
            scrubbing_applied=len(fields_scrubbed) > 0
        )

    def scrub_for_llm_context(
        self,
        data: Dict[str, Any]
    ) -> ScrubbingResult:
        """
        Scrub any data structure before passing to LLM.

        Recursively finds and masks PII patterns.
        Always masks: SSN, full account numbers
        Preserves: Names, general location (city/state)

        Per spec: LLM context must never contain raw SSN or account numbers.

        Args:
            data: Data to scrub

        Returns:
            ScrubbingResult with scrubbed data and audit info
        """
        # Hash original for audit
        original_hash = self._hash_data(data)

        # Make a deep copy
        data_copy = copy.deepcopy(data)

        # Always use LOW clearance for LLM context
        scrubbed_data, fields_scrubbed = self.scrub_dict(data_copy, ClearanceLevel.LOW)

        return ScrubbingResult(
            original_hash=original_hash,
            scrubbed_data=scrubbed_data,
            fields_scrubbed=fields_scrubbed,
            scrubbing_applied=len(fields_scrubbed) > 0
        )


# Module-level singleton
_scrubber: Optional[PIIScrubber] = None


def get_pii_scrubber() -> PIIScrubber:
    """Get or create the PII scrubber singleton."""
    global _scrubber
    if _scrubber is None:
        _scrubber = PIIScrubber()
    return _scrubber
