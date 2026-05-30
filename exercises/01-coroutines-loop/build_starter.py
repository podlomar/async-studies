"""
Section 1 — Build exercise: Staggered greeter / fake downloader
================================================================

Backend scenario
----------------
A utility service needs to "download" three files from different remote servers.
Each download has a different latency. For now, we simulate latency with
asyncio.sleep. In Section 2 you will run these concurrently; here your goal is
to understand what purely sequential awaiting looks like and *measure* the cost.

Tasks
-----
1. Implement download_small, download_medium, and download_large.
2. Implement main() to call them sequentially and report total time.
3. Run the script and verify: total ≈ sum of the individual delays.
4. Leave a comment (marked NOTE) explaining *why* the times add up.

Rules
-----
- Do NOT use time.sleep — use await asyncio.sleep.
- Do NOT import anything beyond `asyncio` and `time`.
- Entry point must be: asyncio.run(main())
"""

import asyncio
import time


async def download_small(name: str) -> None:
    """
    Simulate downloading a small file (~0.3 s latency).

    Steps:
    - Record start time.
    - Print "[name] starting download...".
    - await asyncio.sleep for the delay.
    - Compute elapsed time and print "[name] done in X.XXs".
    """
    # TODO: implement the body of this coroutine.
    ...


async def download_medium(name: str) -> None:
    """
    Simulate downloading a medium file (~0.7 s latency).

    Same structure as download_small; use a longer delay.
    """
    # TODO: implement the body of this coroutine.
    ...


async def download_large(name: str) -> None:
    """
    Simulate downloading a large file (~1.2 s latency).

    Same structure as download_small; use the longest delay.
    """
    # TODO: implement the body of this coroutine.
    ...


async def main() -> None:
    """
    Run all three downloads sequentially and report total elapsed time.

    Steps:
    - Record the overall start time with time.perf_counter().
    - await each download coroutine in order (small → medium → large).
    - Compute and print "Total time: X.XXs".

    NOTE (fill this in after running):
    ___________________________________________________________
    The total time equals the sum of delays because ...
    ___________________________________________________________
    """
    # TODO: record start time.

    # TODO: await download_small with a descriptive name argument, e.g. "small.csv".

    # TODO: await download_medium with a descriptive name argument.

    # TODO: await download_large with a descriptive name argument.

    # TODO: compute elapsed time and print "Total time: X.XXs".
    ...


if __name__ == "__main__":
    asyncio.run(main())
