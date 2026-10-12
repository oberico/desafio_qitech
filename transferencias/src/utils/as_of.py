from datetime import datetime, timezone

from errors import InvalidFormat


def resolve_as_of(payload: dict) -> datetime:
    if "as_of" not in payload:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(payload["as_of"])
    except ValueError as error:
        raise InvalidFormat("as_of", "as_of: not a valid ISO 8601 instant", "esperado data e hora ISO 8601 com fuso") from error
