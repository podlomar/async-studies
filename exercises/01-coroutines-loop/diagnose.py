"""
Section 1 — Diagnose exercise: The missing await
=================================================

Backend scenario
----------------
A junior engineer on your team wrote a quick health-check utility that is
supposed to fetch a status payload from an internal service and log it.
The script runs without crashing, but the output is not what they expected
and the terminal shows a strange warning at exit.

YOUR TASK — answer these questions *before* running this file:
--------------------------------------------------------------

Q1. What Python type does `result` hold at the point of `print(result)`?
    (Hint: think about what `async def` returns when called without `await`.)

Q2. What will the print statement actually output?

Q3. When the script exits, Python may emit a RuntimeWarning.
    - What is the exact text of that warning?
    - Which line of code causes it?
    - Why does Python emit it?

Q4. The engineer wants `result` to hold the string "status: OK — all systems nominal".
    Write the one-word fix that makes this work correctly.

After you have written down your answers, run the file and compare.
"""

import asyncio


async def fetch_status() -> str:
    """
    Simulates an async call to an internal health-check endpoint.
    In a real service this would be: await http_client.get("/health")
    """
    await asyncio.sleep(0.05)   # simulate network round-trip
    return "status: OK — all systems nominal"


async def main() -> None:
    # BUG: fetch_status is called without await.
    # The engineer expects result to be the return value of fetch_status.
    result = fetch_status()     # <-- the bug is on this line

    print(f"Health check response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
