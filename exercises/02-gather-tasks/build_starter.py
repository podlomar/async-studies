"""
Section 2 — Build exercise: Concurrent status checker
======================================================

Backend scenario
----------------
A microservices platform needs a health-check utility that queries several
service endpoints. Currently the checks run serially — total time is the sum
of all individual delays. Your job is to make them run concurrently so that
total time collapses to roughly the *longest* individual delay.

Because requests.get is a blocking call, you must offload it to a thread via
asyncio.to_thread so the event loop stays free to drive the other coroutines
concurrently. This pattern is the bridge between the blocking-IO world and
the async world; you will meet a native async HTTP client in Section 8/9.

Tasks
-----
1. Implement check_service(name, url, delay) — simulates checking one endpoint.
2. Implement check_all_serial(services) — sequential baseline (no concurrency).
3. Implement check_all_concurrent(services) — concurrent version using gather.
4. Implement main() to run both and print a comparison.

Rules
-----
- Do NOT call requests.get directly inside a coroutine — use asyncio.to_thread.
- Do NOT use time.sleep — use await asyncio.sleep.
- Entry point must be: asyncio.run(main())
- Keep a reference to every Task you create.

Service list format
-------------------
Each service is a dict:
    {"name": str, "url": str, "delay": float}

`url` is passed to requests.get.
`delay` simulates post-fetch processing time (await asyncio.sleep(delay)).
"""

import asyncio
import time

import requests


# ---------------------------------------------------------------------------
# A convenient list of services to check. You may adjust URLs or delays.
# If you want zero real network dependency, replace requests.get with a
# stub and leave a comment explaining why.
# ---------------------------------------------------------------------------

SERVICES = [
    {"name": "auth",     "url": "https://httpbin.org/get", "delay": 0.30},
    {"name": "users",    "url": "https://httpbin.org/get", "delay": 0.50},
    {"name": "orders",   "url": "https://httpbin.org/get", "delay": 0.80},
    {"name": "payments", "url": "https://httpbin.org/get", "delay": 0.40},
]


async def check_service(name: str, url: str, delay: float) -> tuple[str, int]:
    """
    Simulate checking a single service endpoint.

    Steps:
    1. Record the start time with time.perf_counter().
    2. Print "[name] checking...".
    3. Call the real HTTP GET without blocking the event loop:
           response = await asyncio.to_thread(requests.get, url)
    4. Simulate additional processing time:
           await asyncio.sleep(delay)
    5. Compute elapsed time and print "[name] OK (X.XXs)".
    6. Return (name, response.status_code) as a tuple.

    Note: asyncio.to_thread runs the blocking function in a thread from the
    default thread pool. The event loop is *free* while the thread is running,
    so other coroutines can make progress — that is the whole point.
    """
    # TODO: implement the body of this coroutine.
    ...


async def check_all_serial(services: list[dict]) -> list[tuple[str, int]]:
    """
    Check every service sequentially (one at a time) and return results.

    Steps:
    1. Record the overall start time.
    2. Iterate `services`; for each service, await check_service(...).
       Collect results in a list.
    3. Print "Serial total: X.XXs".
    4. Return the collected results.

    This is the Section 1 baseline: total time ≈ sum(delays) + network overhead.
    """
    # TODO: record start time.

    results = []
    # TODO: iterate services and await check_service for each.
    #       Append each returned tuple to results.

    # TODO: print "Serial total: X.XXs".

    return results


async def check_all_concurrent(services: list[dict]) -> list[tuple[str, int]]:
    """
    Check every service concurrently using asyncio.gather and return results.

    Steps:
    1. Record the overall start time.
    2. Build a list of coroutines (one check_service call per service).
    3. Await asyncio.gather(*coroutines) to run them all concurrently.
       Store the returned list as `results`.
    4. Print "Concurrent total: X.XXs".
    5. Return results.

    After implementing, observe:
    - The print output shows all "[name] checking..." lines before any
      "[name] OK" line — because all tasks start before any finishes.
    - The total time is close to max(delays), not sum(delays).
    - The result list order matches the order of `services`, not finish order.

    NOTE (fill this in after running):
    ___________________________________________________________
    The wall-clock time collapsed because ...
    ___________________________________________________________
    """
    # TODO: record start time.

    # TODO: build a list of coroutines.
    coroutines = []

    # TODO: await asyncio.gather(*coroutines) and store the result.

    # TODO: print "Concurrent total: X.XXs".

    # TODO: return results.
    ...


async def main() -> None:
    """
    Run serial check, then concurrent check, then print a comparison.

    Steps:
    1. Print "--- Serial ---".
    2. Await check_all_serial(SERVICES) and capture the return value.
    3. Print "--- Concurrent ---".
    4. Await check_all_concurrent(SERVICES) and capture the return value.
    5. Print a one-line comparison, e.g.:
       "Results match: True"  (compare the two result lists)

    Hint: the results lists should be identical in content and order, even
    though the concurrent version finished in a different sequence internally.
    """
    # TODO: print section header and run serial check.

    # TODO: print section header and run concurrent check.

    # TODO: print comparison.
    ...


if __name__ == "__main__":
    asyncio.run(main())
