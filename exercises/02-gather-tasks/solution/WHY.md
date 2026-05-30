# Why things work the way they do — Section 2

## Core concept: `await` in a loop is serial; Tasks are concurrent

When you write:

```python
for url in urls:
    results.append(await fetch(url))
```

the event loop executes one `fetch` coroutine to full completion before starting
the next one. At any moment only a single request is in flight. The total time is
the sum of all individual fetch times — identical to a synchronous `requests.get`
loop, just written with `async`/`await` syntax.

This is the most common asyncio misconception: people see `async` and `await` and
assume concurrency is automatic. It is not. `await` means "run this to completion
and give me the result." Concurrency requires multiple things to be scheduled on
the loop simultaneously.

`asyncio.gather` creates that simultaneous scheduling:

```python
coroutines = [fetch(url) for url in urls]
results = await asyncio.gather(*coroutines)
```

`gather` wraps each coroutine in a `Task` and registers all of them on the event
loop before waiting. When coroutine A suspends (at an `await asyncio.sleep` or
inside `asyncio.to_thread`), the loop immediately switches to coroutine B. All
four coroutines make progress in the gaps between each other's suspension points.
The wall-clock total is therefore bounded by the slowest coroutine alone.

## Why `asyncio.to_thread` is required for `requests.get`

`requests.get` is a blocking OS call. Without `to_thread`, calling it inside a
coroutine would stall the entire event loop — no other coroutine could run until
the HTTP response arrived. Even with `gather`, the requests would effectively
serialize because each one monopolizes the thread.

`asyncio.to_thread(requests.get, url)` runs the blocking function in a worker
thread from the default `ThreadPoolExecutor`. The event loop stays in the main
thread and continues dispatching other coroutines while the network round-trip
happens on a background thread. When the thread finishes, the event loop resumes
the awaiting coroutine with the result.

This is the correct bridge pattern between blocking-IO libraries and asyncio.
In Section 8/9 you will use a natively async HTTP client (`httpx` with
`await client.get(...)`) which eliminates the thread entirely — the socket is
managed directly by the event loop.

## `gather` result ordering

`asyncio.gather` guarantees that result index N corresponds to argument N,
regardless of which coroutine finished first. This is deliberate: it makes
fan-in aggregation predictable. You can zip `results` with the original `services`
list and always get the right pairing:

```python
for svc, (name, status) in zip(services, results):
    assert svc["name"] == name
```

## The fire-and-forget trap explained (Snippet B from diagnose.py)

```python
asyncio.create_task(background_job())   # reference not saved
await asyncio.sleep(0)
# function returns
```

CPython's garbage collector tracks object reference counts. A `Task` is a Python
object. If no variable holds a reference to it, its reference count can drop to
zero at any point and the object can be collected. When a pending `Task` is
garbage-collected, Python emits:

```
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
Task was destroyed but it is pending!
```

And the task's coroutine body simply stops executing — whatever it was doing is
abandoned silently.

The fix is to keep a reference:

```python
task = asyncio.create_task(background_job())
```

If you genuinely want fire-and-forget semantics (start a task and never `await`
it), the idiomatic pattern is to collect tasks in a module-level or class-level
set so they live as long as the application does:

```python
_background_tasks: set[asyncio.Task] = set()

def fire_and_forget(coro):
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
```

The `add_done_callback` removes the task from the set when it finishes, so
completed tasks are not held in memory forever.

## `gather` failure modes: default vs. `return_exceptions=True`

Default behavior (fail-fast):

```python
results = await asyncio.gather(coro_a(), coro_b(), coro_c())
```

If `coro_b` raises `ConnectionError`, `gather` re-raises it immediately.
`coro_a` and `coro_c` continue running (they are not cancelled), but their
return values are silently discarded — you only get the exception.

Best-effort behavior:

```python
results = await asyncio.gather(coro_a(), coro_b(), coro_c(), return_exceptions=True)
```

All three run to completion. `results` is a list where each entry is either the
return value or the exception object. You can inspect the list and distinguish
successes from failures by checking `isinstance(entry, BaseException)`.

The practical rule: use `return_exceptions=True` when you want partial results
from a fan-out (health checks, parallel data fetches where some sources may be
down). Use the default (or `TaskGroup` from Section 6) when all-or-nothing
semantics are correct — if any sub-task fails the whole operation should fail.

## Snippet A from diagnose.py explained

```python
results = []
for url in URLS:
    results.append(await fetch(url))
```

**Answer to Q1:** Exactly one request is in flight at any moment. `await fetch(url)`
runs the entire `fetch` coroutine — including the `asyncio.to_thread` network call
and the `asyncio.sleep` processing delay — to completion before the loop moves to
the next URL.

**Answer to Q2:** ~2.0 s for four URLs each taking ~0.4 s of simulated delay (plus
real network time). The total is approximately `4 * DELAY`.

**Answer to Q3:** Replace the loop with `await asyncio.gather(*[fetch(url) for url in URLS])`.
All four coroutines are scheduled on the loop simultaneously; the total wall-clock
time drops to approximately `1 * DELAY`.
