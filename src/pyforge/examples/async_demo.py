
import asyncio

from pyforge.engine.async_runner import AsyncTaskRunner


async def check_service(service: str) -> dict[str, str]:
    print(f"Starting check: {service}")

    # Simulate waiting for a network response.
    await asyncio.sleep(1)

    print(f"Finished check: {service}")
    return {"service": service, "status": "healthy"}


async def main() -> None:
    runner = AsyncTaskRunner(max_concurrency=2)

    results = await runner.map(
        check_service,
        ["service-A", "service-B", "service-C", "service-D"],
    )

    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
