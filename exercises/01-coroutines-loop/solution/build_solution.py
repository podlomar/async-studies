"""
Section 1 — Build solution: Staggered greeter / fake downloader
===============================================================

Reference implementation. Do not read this until you have attempted
build_starter.py yourself — the learning happens in the struggle.

See solution/WHY.md for a full explanation of every decision here.
"""

import asyncio
import time


async def download_small(name: str) -> None:
    """Simulate downloading a small file with ~0.3 s latency."""
    start = time.perf_counter()
    print(f"[{name}] starting download...")
    await asyncio.sleep(0.3)
    elapsed = time.perf_counter() - start
    print(f"[{name}] done in {elapsed:.2f}s")


async def download_medium(name: str) -> None:
    """Simulate downloading a medium file with ~0.7 s latency."""
    start = time.perf_counter()
    print(f"[{name}] starting download...")
    await asyncio.sleep(0.7)
    elapsed = time.perf_counter() - start
    print(f"[{name}] done in {elapsed:.2f}s")


async def download_large(name: str) -> None:
    """Simulate downloading a large file with ~1.2 s latency."""
    start = time.perf_counter()
    print(f"[{name}] starting download...")
    await asyncio.sleep(1.2)
    elapsed = time.perf_counter() - start
    print(f"[{name}] done in {elapsed:.2f}s")


async def main() -> None:
    """
    Run all three downloads sequentially and report total elapsed time.

    NOTE: The total time equals the sum of the individual delays because each
    `await` suspends main() until that coroutine completes before moving to the
    next one.  The loop only ever has one coroutine in flight at a time — there
    is nothing else scheduled to run.  Concurrency requires creating Tasks so
    that multiple coroutines are all registered on the loop simultaneously; that
    is Section 2.
    """
    overall_start = time.perf_counter()

    await download_small("small.csv")
    await download_medium("medium.csv")
    await download_large("large.csv")

    total = time.perf_counter() - overall_start
    print(f"Total time: {total:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
