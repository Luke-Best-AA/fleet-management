"""Shared helpers for parsing form data and formatting validation errors."""

from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError as PydanticValidationError

# Map Pydantic's internal error types to user-friendly messages
_FRIENDLY_MESSAGES = {
    "int_parsing": "Please enter a valid whole number",
    "int_type": "Please enter a valid whole number",
    "float_parsing": "Please enter a valid number",
    "decimal_parsing": "Please enter a valid number",
    "date_parsing": "Please enter a valid date (YYYY-MM-DD)",
    "date_from_datetime_parsing": "Please enter a valid date",
    "missing": "This field is required",
    "string_too_short": "This field is required",
    "value_error": None,  # use the message from the ValueError
    "bool_parsing": "Please select yes or no",
    "enum": "Please select a valid option",
    "literal_error": "Please select a valid option",
    "url_parsing": "Please enter a valid URL",
    "email_parsing": "Please enter a valid email address",
}


def parse_errors(e: PydanticValidationError) -> dict:
    """Convert Pydantic validation errors to a field->message dict with friendly messages."""
    errors = {}
    for err in e.errors():
        field = err["loc"][-1] if err["loc"] else "_general"
        err_type = err.get("type", "")

        # Use our friendly message if we have one for this error type
        friendly = _FRIENDLY_MESSAGES.get(err_type)
        if friendly is not None:
            msg = friendly
        else:
            # Fall back to the Pydantic message, cleaned up
            msg = err["msg"]
            # Strip Pydantic prefixes
            for prefix in ("Value error, ", "Input should be ", "String should have "):
                if msg.startswith(prefix):
                    msg = msg[len(prefix) :]
                    break

        errors[field] = msg
    return errors


def safe_int(value: str | None, default: int = 0) -> int | str:
    """Convert a form value to int, returning the original string if conversion fails."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return value  # Let Pydantic catch it with a friendly error


def safe_int_or_none(value: str | None) -> int | None | str:
    """Convert a form value to int or None, returning the original string if conversion fails."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return value


def safe_decimal(value: str | None) -> Decimal | None | str:
    """Convert a form value to Decimal or None."""
    if value is None or value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return value


def safe_date(value: str | None) -> date | None | str:
    """Convert a form value to date or None."""
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return value
