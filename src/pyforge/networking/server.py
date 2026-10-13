import asyncio
from typing import Any

from pyforge.networking.protocol import (
    MAX_MESSAGE_BYTES,
    ProtocolError,
    decode_message,
    encode_message,
)


class PyForgeTCPServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None

    @property
    def address(self) -> tuple[str, int]:
        """Return the actual listening address and port."""

        if self._server is None or not self._server.sockets:
            raise RuntimeError("Server has not been started")

        host, port = self._server.sockets[0].getsockname()[:2]
        return host, port

    async def start(self) -> None:
        """Start listening for TCP connections."""

        if self._server is not None:
            raise RuntimeError("Server is already started")

        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
            limit=MAX_MESSAGE_BYTES + 1,
        )

    async def serve_forever(self) -> None:
        if self._server is None:
            raise RuntimeError("Call start() before serve_forever()")

        async with self._server:
            await self._server.serve_forever()

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle multiple newline-delimited requests per connection."""

        try:
            while True:
                try:
                    data = await reader.readline()
                except ValueError:
                    # StreamReader's configured line limit was exceeded.
                    writer.write(encode_message({
                        "ok": False,
                        "error": "Message exceeds the maximum size",
                    }))
                    await writer.drain()
                    break

                if not data:
                    # The client closed its sending side or disconnected.
                    break

                try:
                    request = decode_message(data)
                    response = self._dispatch(request)
                except ProtocolError as exc:
                    response = {
                        "ok": False,
                        "error": str(exc),
                    }

                writer.write(encode_message(response))
                await writer.drain()

        except (ConnectionError, asyncio.CancelledError):
            raise
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    @staticmethod
    def _dispatch(
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and dispatch one request."""

        command = request.get("command")

        if command == "ping":
            return {"ok": True, "message": "pong"}

        if command == "echo":
            message = request.get("message")

            if not isinstance(message, str):
                return {
                    "ok": False,
                    "error": "'message' must be a string",
                }

            return {"ok": True, "message": message}

        return {
            "ok": False,
            "error": f"Unsupported command: {command!r}",
        }
