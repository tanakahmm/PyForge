import json
from typing import Any


MAX_MESSAGE_BYTES = 64 * 1024


class ProtocolError(ValueError):
    """Raised when a network message violates the protocol."""


def encode_message(message: dict[str, Any]) -> bytes:
    """Encode one JSON object followed by a newline."""

    if not isinstance(message, dict):
        raise ProtocolError("Messages must be JSON objects")

    try:
        encoded = (
            json.dumps(message, separators=(",", ":")) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError("Message is not JSON-serializable") from exc

    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Message exceeds the maximum size")

    return encoded


def decode_message(data: bytes) -> dict[str, Any]:
    """Decode one newline-delimited JSON object."""

    if len(data) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Message exceeds the maximum size")

    if not data.endswith(b"\n"):
        raise ProtocolError("Message must end with a newline")

    try:
        decoded = json.loads(data.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Invalid JSON message") from exc

    if not isinstance(decoded, dict):
        raise ProtocolError("Messages must be JSON objects")

    return decoded
