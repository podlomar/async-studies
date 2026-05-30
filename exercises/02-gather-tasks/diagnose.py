"""
Section 2 — Diagnose exercise: The serial loop and the vanishing task
======================================================================

Backend scenario
----------------
Two separate bugs found in real code reviews.

Snippet A: A developer wrote a health-check loop that they believe fires all
requests concurrently. The loop looks reasonable — it uses an async function
and iterates a list of URLs — but timings tell a different story.

Snippet B: A developer added a background cleanup job to a request handler.
They used create_task, which they were told "runs things concurrently". But in
production the cleanup sometimes does not finish, and occasionally does not
run at all.

YOUR TASK — answer these questions *before* running this file
-------------------------------------------------------------

--- Snippet A ---

Q1. The loop body is:
        results.append(await fetch(url))
    How many calls to fetch() are in flight simultaneously at any point?
    (a) all URLs at once  (b) exactly one  (c) it depends on the URL

Q2. If there are 4 URLs each taking ~0.5 s, approximately how long does
    snippet_a() take in total?
    (a) ~0.5 s  (b) ~2.0 s  (c) ~4.0 s

Q3. What single change would make all fetches run concurrently?
    You do not have to write code — describe it in one sentence.

--- Snippet B ---

Q4. After `asyncio.create_task(background_job())` the next line is
    `await asyncio.sleep(0)`. Does background_job always finish?
    What happens if the enclosing coroutine returns before background_job
    finishes?

Q5. Under what condition can a Task object be garbage-collected while still
    pending (i.e., while its coroutine has not completed)?

Q6. The developer's intent was "fire and forget: start background_job and
    let it run while we continue". What is the correct way to do this safely
    so the Task is guaranteed not to be collected early?
    (Hint: you need to keep a reference somewhere.)

After writing down your answers, run this file and observe the timings and
any output from background_job. Then read solution/WHY.md.
"""

import asyncio
import time

import requests


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

URLS = [
    "https://httpbin.org/get",
    "https://httpbin.org/get",
    "https://httpbin.org/get",
    "https://httpbin.org/get",
]

DELAY = 0.4   # simulated per-request processing time


async def fetch(url: str) -> int:
    """Fetch url (offloaded to a thread) and return the status code."""
    response = await asyncio.to_thread(requests.get, url)
    await asyncio.sleep(DELAY)   # simulate processing
    return response.status_code


# ---------------------------------------------------------------------------
# Snippet A — the "concurrent" loop that is secretly serial
# ---------------------------------------------------------------------------

async def snippet_a() -> None:
    """
    The developer believes all four fetches run concurrently.
    Time it and see whether that belief is correct.
    """
    print("Snippet A: starting 4 fetches...")
    t0 = time.perf_counter()

    results = []
    for url in URLS:
        results.append(await fetch(url))   # <-- is this concurrent?

    elapsed = time.perf_counter() - t0
    print(f"Snippet A: got {results} in {elapsed:.2f}s")
    # Question: is elapsed closer to DELAY or to 4 * DELAY?


# ---------------------------------------------------------------------------
# Snippet B — fire-and-forget with a dropped Task reference
# ---------------------------------------------------------------------------

async def background_job() -> None:
    """A background cleanup task that should always run to completion."""
    await asyncio.sleep(0.1)
    # This print may or may not appear, depending on whether the Task survives.
    print("background_job: finished cleanup")


async def snippet_b() -> None:
    """
    The developer creates a task for background work and immediately moves on.
    The task reference is not stored anywhere.
    """
    print("Snippet B: spawning background_job...")

    asyncio.create_task(background_job())  # <-- reference not saved

    # Yield to the loop once, then return immediately.
    await asyncio.sleep(0)

    print("Snippet B: handler returning (did background_job finish yet?)")
    # The enclosing coroutine ends here. What happens to background_job?


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=" * 60)
    await snippet_a()
    print()
    print("=" * 60)
    await snippet_b()
    # Give the event loop one more tick so any pending output can flush.
    await asyncio.sleep(0.2)


if __name__ == "__main__":
    asyncio.run(main())
