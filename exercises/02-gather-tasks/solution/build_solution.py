"""
Section 2 — Build solution: Concurrent status checker
======================================================

Reference implementation. Do not read this until you have attempted
build_starter.py yourself — the learning happens in the struggle.

See solution/WHY.md for a full explanation of every decision here.
"""

import asyncio
import time

import requests


SERVICES = [
    {"name": "auth",     "url": "https://httpbin.org/get", "delay": 0.30},
    {"name": "users",    "url": "https://httpbin.org/get", "delay": 0.50},
    {"name": "orders",   "url": "https://httpbin.org/get", "delay": 0.80},
    {"name": "payments", "url": "https://httpbin.org/get", "delay": 0.40},
]


async def check_service(name: str, url: str, delay: float) -> tuple[str, int]:
    """Check a single service endpoint and return (name, status_code)."""
    start = time.perf_counter()
    print(f"[{name}] checking...")

    # requests.get is a blocking call. asyncio.to_thread runs it in a worker
    # thread from the default ThreadPoolExecutor, freeing the event loop to
    # drive other coroutines while the network round-trip is in progress.
    response = await asyncio.to_thread(requests.get, url)

    # Simulate post-fetch processing (e.g. JSON parsing, DB lookup).
    await asyncio.sleep(delay)

    elapsed = time.perf_counter() - start
    print(f"[{name}] OK ({elapsed:.2f}s)")
    return (name, response.status_code)


async def check_all_serial(services: list[dict]) -> list[tuple[str, int]]:
    """Run each service check sequentially. Total ≈ sum(delays)."""
    start = time.perf_counter()

    results = []
    for svc in services:
        result = await check_service(svc["name"], svc["url"], svc["delay"])
        results.append(result)

    elapsed = time.perf_counter() - start
    print(f"Serial total: {elapsed:.2f}s")
    return results


async def check_all_concurrent(services: list[dict]) -> list[tuple[str, int]]:
    """
    Run every service check concurrently using gather. Total ≈ max(delays).

    asyncio.gather accepts coroutines (or Tasks). It wraps each coroutine in
    a Task under the hood, registers all of them on the event loop at once,
    and suspends until the last one completes. The returned list preserves
    the order of the input arguments — gather[0] is the result of services[0]
    regardless of which service responded first.

    NOTE: The wall-clock time collapsed because all four check_service
    coroutines are registered on the loop before any of them is awaited in
    isolation. While one coroutine is suspended inside asyncio.to_thread or
    asyncio.sleep, the event loop switches to another. Maximum overlap means
    total time is bounded by the slowest single coroutine, not their sum.
    """
    start = time.perf_counter()

    coroutines = [
        check_service(svc["name"], svc["url"], svc["delay"])
        for svc in services
    ]

    # gather fans out to all coroutines concurrently and fans back in here.
    results: list[tuple[str, int]] = await asyncio.gather(*coroutines)

    elapsed = time.perf_counter() - start
    print(f"Concurrent total: {elapsed:.2f}s")
    return list(results)


async def main() -> None:
    print("--- Serial ---")
    serial_results = await check_all_serial(SERVICES)

    print()
    print("--- Concurrent ---")
    concurrent_results = await check_all_concurrent(SERVICES)

    print()
    print(f"Results match: {serial_results == concurrent_results}")


if __name__ == "__main__":
    asyncio.run(main())
