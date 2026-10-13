import asyncio
from pyforge.networking import PyForgeTCPServer,send_request

async def main()->None:
    server=PyForgeTCPServer(host='127.0.0.1',port=0)
    await server.start()

    try:
        host,port=server.address
        print(f"server listening at {host}:{port}")
        
        response=await send_request(host,port,{"command":"ping"},)
        print("Ping Response")

        response = await send_request(
            host,
            port,
            {"command": "echo", "message": "Hello, PyForge!"},
        )
        print("Echo response:", response)

    finally:
        await server.close()


if __name__ == "__main__":
    asyncio.run(main())

