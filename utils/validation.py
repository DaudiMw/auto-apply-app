import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


def validate_address(address: Dict[str, Any]) -> bool:
    """Validates US address fields: street, city, state, zip_code, country."""
    if not address:
        return False

    street = str(address.get("street") or "").strip()
    city = str(address.get("city") or "").strip()
    state = str(address.get("state") or "").strip()
    zip_code = str(address.get("zip_code") or "").strip()
    country = str(address.get("country") or "").strip()

    if not street or not city or not state or not zip_code:
        logger.debug("Address validation failed: missing required field")
        return False

    # Zip code: 5 digits, optionally with hyphen and 4 digits
    zip_pattern = r"^\d{5}(-\d{4})?$"
    if not re.match(zip_pattern, zip_code):
        logger.debug("Address validation failed: invalid zip code format")
        return False

    return True
