import asyncio
from typing import Any

from pyforge.networking.protocol import decode_message, encode_message


async def send_request(
    host: str,
    port: int,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Send one request and return the server's response."""

    reader, writer = await asyncio.open_connection(host, port)

    try:
        writer.write(encode_message(request))
        await writer.drain()

        response_data = await reader.readline()

        if not response_data:
            raise ConnectionError("Server closed without a response")

        return decode_message(response_data)

    finally:
        writer.close()
        await writer.wait_closed()
