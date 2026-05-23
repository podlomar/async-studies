# 2.3 Tasks and Futures

> **Phase 2 — Asyncio Fundamentals**
>
> You know that `create_task` enables concurrent execution. Now learn the full API for running many coroutines at once, collecting their results, and understanding the `Future` that sits underneath it all.

---

## What Is a Task?

A **Task** is a coroutine that has been handed to the event loop to run concurrently. It wraps the coroutine, tracks its state, and holds its result (or exception) when done.

```python
import asyncio

async def work(n):
    await asyncio.sleep(n)
    return n * 10

async def main():
    task = asyncio.create_task(work(2))

    print(type(task))        # <class 'asyncio.Task'>
    print(task.done())       # False — still running
    print(task.cancelled())  # False

    result = await task      # wait for it to finish

    print(task.done())       # True
    print(task.result())     # 20

asyncio.run(main())
```

`create_task` schedules the coroutine immediately. The task starts running the next time the event loop gets control — which happens at the first `await` after `create_task`.

---

## What Is a Future?

A **Future** is a lower-level object that represents a value that does not exist yet. It is a promise: "I will have a result eventually."

```
Future states:
  Pending  → result not yet available
  Done     → result set (or exception, or cancelled)
```

You rarely create Futures directly in application code. They appear when you:

- Wrap a callback-based API in async code
- Interface with the loop's low-level transport/protocol layer
- Use `loop.run_in_executor()` (returns a Future)

The key point: **Task is a subclass of Future**. Everything that works on a Future (awaiting, cancelling, adding callbacks) also works on a Task.

```python
import asyncio

async def demo():
    loop = asyncio.get_running_loop()

    # A raw Future — no coroutine attached
    fut = loop.create_future()
    print(fut.done())    # False

    # Set its result from the outside
    fut.set_result(42)
    print(fut.done())    # True
    print(await fut)     # 42

asyncio.run(demo())
```

In practice: think of `Future` as the contract ("a result will arrive") and `Task` as its implementation for coroutines ("run this coroutine and put the result in a Future").

---

## `await coro()` vs `create_task(coro())`

This is the most important distinction in asyncio. Revisited here with full detail.

```python
import asyncio
import time

async def fetch(name, delay):
    print(f"  {name}: start")
    await asyncio.sleep(delay)
    print(f"  {name}: done")
    return name

# ── Sequential ─────────────────────────────────────────
async def sequential():
    r1 = await fetch("A", 1)   # A must finish before B starts
    r2 = await fetch("B", 1)
    return r1, r2

# ── Concurrent ─────────────────────────────────────────
async def concurrent():
    t1 = asyncio.create_task(fetch("A", 1))  # A enters ready queue
    t2 = asyncio.create_task(fetch("B", 1))  # B enters ready queue
    r1 = await t1   # both running; we just wait for A's result
    r2 = await t2
    return r1, r2

for label, fn in [("Sequential", sequential), ("Concurrent", concurrent)]:
    start = time.perf_counter()
    asyncio.run(fn())
    print(f"{label}: {time.perf_counter() - start:.2f}s\n")
```

Output:
```
  A: start
  A: done
  B: start
  B: done
Sequential: 2.00s

  A: start
  B: start
  A: done
  B: done
Concurrent: 1.00s
```

The rule: **`await coro()` is sequential. `create_task(coro())` followed by `await task` is concurrent.**

---

## `asyncio.gather()`

`gather` is the most common way to run multiple coroutines or tasks concurrently and collect all their results.

```python
results = await asyncio.gather(coro1(), coro2(), coro3())
```

It accepts any mix of coroutines, Tasks, or Futures. It returns a list of results in the **same order as the inputs**, regardless of which finishes first.

```python
import asyncio

async def step(name, delay, value):
    await asyncio.sleep(delay)
    return value

async def main():
    results = await asyncio.gather(
        step("slow", 1.5, "A"),
        step("fast", 0.5, "B"),
        step("medium", 1.0, "C"),
    )
    print(results)  # ['A', 'B', 'C'] — input order, not completion order

asyncio.run(main())
```

### Error handling with `gather`

By default, if one coroutine raises an exception, `gather` propagates it immediately and cancels the others.

```python
async def main():
    try:
        results = await asyncio.gather(
            step("ok", 0.5, "good"),
            bad_step(),           # raises after 0.3s
            step("ok2", 1.0, "also good"),
        )
    except ValueError as e:
        print(f"caught: {e}")
```

To collect all results and exceptions without short-circuiting, use `return_exceptions=True`:

```python
results = await asyncio.gather(
    step("ok", 0.5, "good"),
    bad_step(),
    step("ok2", 1.0, "also good"),
    return_exceptions=True,
)
# results = ['good', ValueError('something went wrong'), 'also good']

for r in results:
    if isinstance(r, Exception):
        print(f"failed: {r}")
    else:
        print(f"ok: {r}")
```

`return_exceptions=True` is useful for fan-out workloads where you want partial results even if some requests fail.

---

## `asyncio.wait()`

`wait` gives you more control than `gather`: it returns two sets of tasks — done and pending — and lets you decide what to do next.

```python
done, pending = await asyncio.wait(tasks, ...)
```

### `return_when` options

| Value | Meaning |
|---|---|
| `ALL_COMPLETED` (default) | Wait until every task is done |
| `FIRST_COMPLETED` | Return as soon as any one task finishes |
| `FIRST_EXCEPTION` | Return as soon as any task raises an exception |

```python
import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)
    return name

async def main():
    tasks = {
        asyncio.create_task(fetch("A", 1.5)),
        asyncio.create_task(fetch("B", 0.5)),
        asyncio.create_task(fetch("C", 1.0)),
    }

    # Return as soon as the first task finishes
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    print(f"First done: {[t.result() for t in done]}")
    print(f"Still running: {len(pending)}")

    # Cancel the rest
    for t in pending:
        t.cancel()

    # Wait for cancellations to complete
    await asyncio.wait(pending)

asyncio.run(main())
```

`wait` requires a set or list of **Tasks** (not bare coroutines). Wrap coroutines with `create_task` first.

### `wait` vs `gather`

| | `gather` | `wait` |
|---|---|---|
| Input | coroutines, tasks, futures | tasks only |
| Returns | list of results | (done set, pending set) |
| Order | preserves input order | unordered sets |
| On exception | propagates (or collects) | task holds it in `.exception()` |
| Use when | you want all results, simply | you need to react to partial completion |

---

## `asyncio.as_completed()`

`as_completed` yields tasks in the order they **finish**, not the order they were created. It is the right tool when you want to process each result as soon as it arrives.

```python
import asyncio
import time

start = time.perf_counter()

async def fetch(name, delay):
    await asyncio.sleep(delay)
    return name, delay

async def main():
    coros = [
        fetch("slow",   2.0),
        fetch("fast",   0.3),
        fetch("medium", 1.0),
    ]

    async for completed in asyncio.as_completed(coros):
        name, delay = await completed
        elapsed = time.perf_counter() - start
        print(f"[{elapsed:.2f}s] {name} finished (took {delay}s)")

asyncio.run(main())
```

Output:
```
[0.30s] fast finished (took 0.3s)
[1.00s] medium finished (took 1.0s)
[2.00s] slow finished (took 2.0s)
```

`as_completed` is ideal for workloads where you want to start processing early results while slow ones are still in flight — for example, displaying search results as they arrive, or storing downloaded files as soon as each completes.

---

## Task Cancellation

A task can be cancelled from the outside. Cancellation works by injecting a `CancelledError` exception into the coroutine at its next `await` point.

```python
import asyncio

async def long_job():
    try:
        print("job: starting")
        await asyncio.sleep(10)
        print("job: done")     # never reached if cancelled
    except asyncio.CancelledError:
        print("job: cancelled — cleaning up")
        raise   # always re-raise CancelledError

async def main():
    task = asyncio.create_task(long_job())

    await asyncio.sleep(0.5)  # let it start

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("main: confirmed cancelled")
    
    print(f"task.cancelled(): {task.cancelled()}")

asyncio.run(main())
```

Output:
```
job: starting
job: cancelled — cleaning up
main: confirmed cancelled
task.cancelled(): True
```

Important rules:
- Always `raise` inside a `CancelledError` handler — swallowing it prevents proper shutdown.
- Cancellation only lands at `await` points. Synchronous code between `await` calls cannot be interrupted.
- `task.cancel()` returns `True` if the cancellation was requested (the task was still running), `False` if the task was already done.

---

## Task Callbacks

You can attach a callback to a task that fires when it completes — whether it succeeded, failed, or was cancelled.

```python
import asyncio

async def work():
    await asyncio.sleep(0.5)
    return 42

def on_done(task):
    if task.cancelled():
        print("cancelled")
    elif task.exception():
        print(f"failed: {task.exception()}")
    else:
        print(f"result: {task.result()}")

async def main():
    task = asyncio.create_task(work())
    task.add_done_callback(on_done)
    await task

asyncio.run(main())
# result: 42
```

Callbacks are synchronous functions called by the event loop. They receive the task as their only argument. They're useful for logging, metrics, or triggering follow-up work without awaiting the task directly.

---

## Fan-Out / Fan-In Pattern

**Fan-out**: dispatch one unit of work to many concurrent workers.  
**Fan-in**: collect all results back into one place.

This is the most common pattern in real async applications: fetch from 50 APIs, process 200 files, query 10 database shards simultaneously.

```python
import asyncio
import time

# Simulated I/O operation
async def fetch_item(item_id):
    await asyncio.sleep(0.1)   # simulate network latency
    return {"id": item_id, "value": item_id * 100}

async def process(data):
    await asyncio.sleep(0.05)  # simulate processing
    return data["value"] + 1

async def main():
    item_ids = list(range(20))

    # Fan-out: fetch all items concurrently
    raw = await asyncio.gather(*[fetch_item(i) for i in item_ids])

    # Fan-in: process all results concurrently
    processed = await asyncio.gather(*[process(r) for r in raw])

    print(f"Processed {len(processed)} items")
    print(f"First five: {processed[:5]}")

start = time.perf_counter()
asyncio.run(main())
print(f"Total: {time.perf_counter() - start:.2f}s")
# Total: ~0.15s instead of ~3.0s sequential
```

---

## Key Concepts Summary

**Task** — a coroutine wrapped and scheduled on the event loop. Subclass of Future. Created with `asyncio.create_task()`.

**Future** — a placeholder for a result that does not exist yet. The base class Tasks build on.

**`gather`** — run many coroutines/tasks concurrently, return all results in input order. Short-circuits on exception unless `return_exceptions=True`.

**`wait`** — run tasks and return done/pending sets. Fine-grained control via `return_when`. Requires Task objects.

**`as_completed`** — iterate over tasks in completion order. Process results as they arrive.

**Cancellation** — inject `CancelledError` into a task at its next await point. Always re-raise in handlers.

**Fan-out / fan-in** — dispatch concurrent work with `gather` or `create_task`, collect results when done.

---

## Practice Exercises

### Exercise 1 — `gather` result ordering

Verify that `gather` preserves input order even when tasks finish in a different order.

```python
import asyncio

async def fetch(label, delay, value):
    await asyncio.sleep(delay)
    print(f"  {label} finished")
    return value

async def main():
    results = await asyncio.gather(
        fetch("slow",   1.5, "first"),
        fetch("fast",   0.2, "second"),
        fetch("medium", 0.8, "third"),
    )
    print(f"Results: {results}")
    # Expect: ['first', 'second', 'third'] — input order, despite completion order

asyncio.run(main())
```

**Goal:** Confirm that gather is order-preserving.

---

### Exercise 2 — Handle partial failures

Use `return_exceptions=True` to process a mix of successes and failures.

```python
import asyncio

async def risky(n):
    await asyncio.sleep(0.1 * n)
    if n % 3 == 0:
        raise ValueError(f"n={n} is divisible by 3")
    return n * 10

async def main():
    results = await asyncio.gather(
        *[risky(n) for n in range(1, 8)],
        return_exceptions=True,
    )

    for i, r in enumerate(results, 1):
        if isinstance(r, Exception):
            print(f"  task {i}: FAILED — {r}")
        else:
            print(f"  task {i}: ok — {r}")

asyncio.run(main())
```

**Goal:** Know how to safely gather results from unreliable operations.

---

### Exercise 3 — First-completed pattern

Fetch the same data from two sources simultaneously and use whichever replies first.

```python
import asyncio
import random

async def fetch_from(source, base_delay):
    delay = base_delay + random.uniform(0, 0.5)
    await asyncio.sleep(delay)
    return source, delay

async def main():
    tasks = {
        asyncio.create_task(fetch_from("primary",   0.3)),
        asyncio.create_task(fetch_from("secondary", 0.2)),
    }

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    winner = done.pop()
    source, delay = winner.result()
    print(f"Winner: {source} ({delay:.2f}s)")

    for t in pending:
        t.cancel()
    await asyncio.wait(pending)

asyncio.run(main())
```

Run it several times. The winner changes based on random delays.

**Goal:** Use `FIRST_COMPLETED` to implement a "fastest replica wins" pattern.

---

### Exercise 4 — Process results as they arrive

Simulate a dashboard that updates as data comes in from slow sources.

```python
import asyncio
import time

start = time.perf_counter()

async def data_source(name, delay, value):
    await asyncio.sleep(delay)
    return name, value

async def main():
    sources = [
        data_source("inventory",   1.5, {"stock": 42}),
        data_source("pricing",     0.4, {"price": 9.99}),
        data_source("reviews",     1.0, {"rating": 4.3}),
        data_source("shipping",    0.7, {"eta": "2 days"}),
        data_source("recommended", 1.8, {"items": [1, 2, 3]}),
    ]

    print("Loading product page...")
    async for task in asyncio.as_completed(sources):
        name, value = await task
        elapsed = time.perf_counter() - start
        print(f"  [{elapsed:.2f}s] {name}: {value}")

    print(f"Page fully loaded at {time.perf_counter() - start:.2f}s")

asyncio.run(main())
```

**Goal:** Feel the difference between waiting for everything (gather) and updating progressively (as_completed).

---

### Exercise 5 — Cancellation with cleanup

Write a long-running task that cleans up properly when cancelled.

```python
import asyncio

async def download(url, chunk_size=3):
    downloaded = 0
    try:
        print(f"  Starting download: {url}")
        for i in range(chunk_size):
            await asyncio.sleep(0.3)   # simulate downloading a chunk
            downloaded += 1
            print(f"  Chunk {downloaded} of {chunk_size} done")
        return f"{url}: complete"
    except asyncio.CancelledError:
        print(f"  Download cancelled after {downloaded} chunks — freeing connection")
        raise

async def main():
    task = asyncio.create_task(download("https://example.com/file.bin"))

    await asyncio.sleep(0.7)   # let it download 2 chunks, then cancel

    print("Cancelling...")
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("Download stopped cleanly")

asyncio.run(main())
```

**Goal:** Understand how to write cancellation-safe coroutines that release resources before exiting.

---

### Challenge — Parallel API fetcher with rate limiting

Fetch 10 "API endpoints" concurrently, but limit to 3 in-flight requests at a time using a `Semaphore` (preview of Phase 3).

```python
import asyncio
import time

async def api_call(endpoint_id, semaphore):
    async with semaphore:
        print(f"  [{time.perf_counter():.2f}] fetching endpoint {endpoint_id}")
        await asyncio.sleep(0.4)   # simulate API latency
        return {"id": endpoint_id, "data": endpoint_id * 7}

async def main():
    sem = asyncio.Semaphore(3)   # at most 3 concurrent requests

    tasks = [api_call(i, sem) for i in range(10)]
    results = await asyncio.gather(*tasks)

    print(f"\nGot {len(results)} results")
    for r in results:
        print(f"  endpoint {r['id']}: {r['data']}")

start = time.perf_counter()
asyncio.run(main())
print(f"Total: {time.perf_counter() - start:.2f}s")
# With semaphore(3): ~4 batches × 0.4s ≈ 1.6s
# Without limiting: all 10 at once ≈ 0.4s
```

Run it once with `Semaphore(3)` and once with `Semaphore(10)` (no real limit). Observe the time difference and the interleaving pattern.

---

## What's Next

You can now run many coroutines concurrently, collect results with `gather`, react to completions with `as_completed`, and cancel tasks cleanly. That completes Phase 2 — the core asyncio mental model.

**Phase 3** moves into building real applications: async HTTP clients, synchronization primitives for coordinating shared resources, and production-grade cancellation and error handling.
