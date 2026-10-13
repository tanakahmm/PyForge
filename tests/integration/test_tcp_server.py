import asyncio
import json

from pyforge.networking.client import send_request
from pyforge.networking.server import PyForgeTCPServer


def test_ping_and_echo_over_tcp():
    async def scenario():
        server = PyForgeTCPServer(host="127.0.0.1", port=0)
        await server.start()

        try:
            host, port = server.address

            ping = await send_request(
                host, port, {"command": "ping"}
            )
            assert ping == {"ok": True, "message": "pong"}

            echo = await send_request(
                host,
                port,
                {"command": "echo", "message": "hello"},
            )
            assert echo == {"ok": True, "message": "hello"}

        finally:
            await server.close()

    asyncio.run(scenario())


def test_server_rejects_unknown_commands():
    async def scenario():
        server = PyForgeTCPServer(host="127.0.0.1", port=0)
        await server.start()

        try:
            host, port = server.address
            response = await send_request(
                host, port, {"command": "launch_missiles"}
            )

            assert response["ok"] is False
            assert "Unsupported command" in response["error"]
        finally:
            await server.close()

    asyncio.run(scenario())


def test_server_rejects_invalid_json():
    async def scenario():
        server = PyForgeTCPServer(host="127.0.0.1", port=0)
        await server.start()

        try:
            host, port = server.address
            reader, writer = await asyncio.open_connection(host, port)

            try:
                writer.write(b"{invalid json}\n")
                await writer.drain()

                response = json.loads(
                    await reader.readline()
                )

                assert response["ok"] is False
                assert response["error"] == "Invalid JSON message"
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            await server.close()

    asyncio.run(scenario())
