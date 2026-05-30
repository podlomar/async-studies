# Project conventions for the asyncio learning lab

## Environment
- Python 3.12 on Ubuntu. Assume modern syntax (3.10+ match, 3.11+ TaskGroup/timeout/except*).
- Prefer stdlib. Allowed extras: `requests`, `httpx`. No web frameworks, no Celery, no Redis libs.

## Asyncio rules
- Always enter via `asyncio.run(main())`. Never call `get_event_loop()` (deprecated path in 3.12).
- Inside coroutines, never use blocking calls (`time.sleep`, `requests.get`, blocking file IO)
  unless the exercise is *specifically* about offloading them via `asyncio.to_thread` / executors.
- Prefer `asyncio.TaskGroup` over bare `gather` for new structured-concurrency code; show both when teaching.
- Always handle `asyncio.CancelledError` correctly: never swallow it with bare `except Exception`.

## Teaching style
- Each exercise is grounded in a realistic backend scenario.
- Starter files contain TODOs and docstrings only — never the solution.
- Diagnose exercises: include questions for the learner to answer before running.
- Provide tests using `unittest.IsolatedAsyncioTestCase` (stdlib, no pytest needed).
- Keep explanations concrete; prefer "here's what actually happens on the loop" over hand-waving.
