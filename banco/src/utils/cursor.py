import base64
import binascii
import hashlib
import hmac

from constants import CURSOR_SECRET
from errors.custom_errors import InvalidSchema


def encode_cursor(entry_id: int) -> str:
    payload = str(entry_id)
    return base64.urlsafe_b64encode(f"{payload}.{_sign(payload)}".encode()).decode()


def decode_cursor(cursor: str) -> int:
    try:
        payload, signature = base64.urlsafe_b64decode(cursor.encode()).decode().split(".")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise InvalidSchema("cursor: invalid cursor")
    if not payload.isdigit() or not hmac.compare_digest(signature, _sign(payload)):
        raise InvalidSchema("cursor: invalid cursor")
    return int(payload)


def _sign(payload: str) -> str:
    return hmac.new(CURSOR_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
