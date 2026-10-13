import pytest

from pyforge.networking.protocol import (
    ProtocolError,
    decode_message,
    encode_message,
)


def test_json_message_round_trip():
    message = {"command": "echo", "message": "hello"}

    assert decode_message(encode_message(message)) == message


def test_message_requires_newline():
    with pytest.raises(ProtocolError, match="newline"):
        decode_message(b'{"command":"ping"}')


def test_invalid_json_is_rejected():
    with pytest.raises(ProtocolError, match="Invalid JSON"):
        decode_message(b"{invalid json}\n")


def test_non_object_json_is_rejected():
    with pytest.raises(ProtocolError, match="JSON objects"):
        decode_message(b'["hello"]\n')


def test_oversized_message_is_rejected():
    with pytest.raises(ProtocolError, match="maximum size"):
        encode_message({"message": "x" * (64 * 1024)})
