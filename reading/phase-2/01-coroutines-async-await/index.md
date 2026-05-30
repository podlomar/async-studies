# 2.1 Coroutines and `async` / `await`

> **Phase 2 — Asyncio Fundamentals**
>
> You know *why* async exists. Now learn the syntax and mental model that make it work.

---

## What Is a Coroutine?

A **coroutine** is a function that can be paused mid-execution and resumed later, without losing its local state.

Regular functions run to completion once called. A coroutine runs until it decides to pause — at an `await` expression — hands control back to the event loop, and picks up exactly where it left off when the event loop resumes it.

Think of it like a bookmark in a book: the coroutine marks its place, the event loop does other work, then returns and continues reading from the same page.

---

## Functions vs Coroutine Objects

This is the single most common source of confusion for beginners. Pay close attention.

### A regular function

```python
def greet(name):
    return f"Hello, {name}"

result = greet("Alice")   # executes immediately
print(result)             # Hello, Alice
```

Calling `greet("Alice")` runs the function body right now and returns the result.

### An async function

```python
import asyncio

async def greet(name):
    return f"Hello, {name}"

result = greet("Alice")   # does NOT execute the body
print(result)             # <coroutine object greet at 0x...>
print(type(result))       # <class 'coroutine'>
```

Calling `greet("Alice")` **does not run the function body**. It returns a **coroutine object** — a suspended computation that hasn't started yet.

To actually run it, you need to either:

```python
# Option 1: run it as the top-level entry point
asyncio.run(greet("Alice"))

# Option 2: await it inside another coroutine
async def main():
    result = await greet("Alice")
    print(result)  # Hello, Alice
```

> **Rule:** Defining a function with `async def` changes what calling it returns. You never execute the body by calling the function alone — you need `await` or `asyncio.run()`.

---

## The `await` Keyword

`await` does two things simultaneously:

1. **Suspends** the current coroutine until the awaitable it receives is done
2. **Yields control** back to the event loop so other coroutines can run in the meantime

```python
import asyncio

async def slow_task(name, delay):
    print(f"{name}: starting")
    await asyncio.sleep(delay)      # suspend here, let others run
    print(f"{name}: done after {delay}s")
    return name

async def main():
    result = await slow_task("Task A", 2)
    print(f"Result: {result}")

asyncio.run(main())
```

Output:
```
Task A: starting
Task A: done after 2s
Result: Task A
```

Here `main` suspends at `await slow_task(...)`, which itself suspends at `await asyncio.sleep(2)`. When the sleep finishes, the chain resumes in reverse.

### What `await` can receive

`await` only works with **awaitables**. An awaitable is any object that implements the `__await__` protocol. The three kinds you'll encounter are:

| Awaitable | What it is |
|---|---|
| Coroutine object | Result of calling an `async def` function |
| `asyncio.Task` | A coroutine scheduled to run concurrently |
| `asyncio.Future` | A low-level placeholder for a future result |

```python
async def main():
    # Awaiting a coroutine object
    result = await some_coroutine()

    # Awaiting a Task (runs concurrently with other tasks)
    task = asyncio.create_task(some_coroutine())
    result = await task

    # Awaiting a built-in awaitable
    await asyncio.sleep(1)
```

You cannot `await` a regular function call, a `threading.Thread`, or most other objects. Doing so raises `TypeError: object NoneType can't be used in 'await' expression` (or similar).

---

## Suspension Points

A **suspension point** is any `await` expression in your code. It is the *only* place where a coroutine can be paused.

```python
async def pipeline(url):
    print("A")
    data = await fetch(url)      # suspension point 1
    print("B")
    result = await process(data) # suspension point 2
    print("C")
    await save(result)           # suspension point 3
    print("D")
```

Between any two suspension points, the coroutine runs **atomically** — no other coroutine can interleave. This is the key safety property of async code that makes it easier to reason about than threaded code (see section 1.2).

The event loop can only schedule other work at suspension points. If your coroutine does heavy CPU work between two `await` calls, it **blocks the entire event loop** for that duration. This is called "blocking the event loop" and is the primary mistake to avoid in async code.

```python
# Bad: blocks the event loop for the entire computation
async def bad_worker():
    await asyncio.sleep(0)
    result = sum(i * i for i in range(10_000_000))  # blocks event loop here
    return result

# Good: offload to a thread pool (covered in Phase 6)
async def good_worker():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: sum(i * i for i in range(10_000_000)))
    return result
```

---

## `asyncio.sleep()` vs `time.sleep()`

This is the critical milestone for Phase 2. These two functions look similar but behave completely differently inside async code.

### `time.sleep(n)`

Blocks the **entire thread** for `n` seconds. Since asyncio runs on a single thread, blocking the thread blocks the entire event loop. No other coroutine can run.

```python
import asyncio
import time

async def task(name, delay):
    print(f"{name}: start")
    time.sleep(delay)           # blocks the whole event loop
    print(f"{name}: done")

async def main():
    await asyncio.gather(
        task("A", 2),
        task("B", 2),
        task("C", 2),
    )

start = time.perf_counter()
asyncio.run(main())
print(f"Total: {time.perf_counter() - start:.1f}s")
```

Output:
```
A: start
A: done       ← B and C are frozen until A finishes
B: start
B: done
C: start
C: done
Total: 6.0s   ← sequential, NOT concurrent
```

### `asyncio.sleep(n)`

Suspends the **current coroutine** for `n` seconds and yields control back to the event loop. Other coroutines run freely during that time.

```python
import asyncio
import time

async def task(name, delay):
    print(f"{name}: start")
    await asyncio.sleep(delay)  # suspends this coroutine, others run
    print(f"{name}: done")

async def main():
    await asyncio.gather(
        task("A", 2),
        task("B", 2),
        task("C", 2),
    )

start = time.perf_counter()
asyncio.run(main())
print(f"Total: {time.perf_counter() - start:.1f}s")
```

Output:
```
A: start
B: start
C: start      ← all three start before any finishes
A: done
B: done
C: done
Total: 2.0s   ← concurrent, not sequential
```

The rule: **inside async code, never use `time.sleep()`**. Always use `await asyncio.sleep()`.

More broadly: never call any blocking function directly in a coroutine. The async ecosystem provides async-native replacements for most blocking operations (`aiohttp` instead of `requests`, `aiofiles` instead of `open`, `asyncpg` instead of `psycopg2`).

---

## Cooperative Scheduling

The word "cooperative" means that coroutines must voluntarily yield control. The event loop never forcibly interrupts them (unlike the OS with threads).

This has two consequences:

**Good:** Races between coroutines are predictable. A coroutine holds the CPU from one `await` to the next, so no interleaving happens in that window.

**Bad:** A poorly written coroutine that never yields can starve all others. One stuck coroutine freezes the entire program.

```python
async def cooperative():
    for i in range(5):
        print(f"  step {i}")
        await asyncio.sleep(0)   # yield to event loop, then continue

async def starving():
    for i in range(5):
        print(f"  step {i}")
        # no await — never yields
```

`await asyncio.sleep(0)` is the async equivalent of "yield to scheduler". It suspends for zero time but still gives the event loop a chance to run other coroutines. You'll use this when writing long-running loops that shouldn't block others.

---

## Non-Blocking Execution

"Non-blocking" means the event loop thread is never made to wait. While one coroutine is suspended waiting on I/O, the event loop picks up the next ready coroutine and runs it. The thread stays busy.

```
Coroutine A: [setup]--[await network]--[process response]
Coroutine B:           [setup]--[await db]--[process result]
Coroutine C:                     [setup]--[await file]--[done]
Event loop:  [A runs][B runs][C runs][A resumes][B resumes][C resumes]
Thread:      [active throughout — never waiting]
```

Compare with threads, where a blocked thread sits idle consuming memory and a kernel scheduler slot while doing nothing useful. Async eliminates that waste.

---

## `asyncio.run()`

`asyncio.run(coro)` is the standard entry point for any async program. It:

1. Creates a new event loop
2. Runs the given coroutine to completion
3. Closes the loop and cleans up

```python
import asyncio

async def main():
    print("Hello from async land")
    await asyncio.sleep(1)
    print("Done")

asyncio.run(main())  # the only sync→async bridge you need at the top level
```

Important constraints:
- `asyncio.run()` cannot be called from inside a running event loop. Inside an async function, `await coro()` is always the right approach.
- Calling `asyncio.run()` inside a Jupyter notebook raises an error because Jupyter already runs an event loop — use `await` directly there, or `nest_asyncio`.

---

## Key Concepts Summary

**Coroutine** — a function defined with `async def` whose body is not executed when you call it. You get back a coroutine object. Execution happens only when awaited.

**Coroutine object** — a suspended computation. Returned by calling an `async def` function. Implements `__await__`.

**`await`** — suspends the current coroutine, yields control to the event loop, and resumes when the awaitable is done.

**Suspension point** — any `await` in your code. The only place the event loop can switch to another coroutine.

**Awaitable** — any object that can be used with `await`: coroutine objects, Tasks, Futures.

**Cooperative scheduling** — coroutines yield voluntarily at `await` points. No preemption.

**Non-blocking** — the event loop thread never waits. When one coroutine yields, another runs immediately.

---

## Practice Exercises

### Exercise 1 — Observe the coroutine object

See with your own eyes that calling an async function does not run it.

```python
import asyncio

async def say_hello():
    print("Hello!")
    return 42

# This does NOT print anything and does NOT return 42
coro = say_hello()
print(type(coro))   # <class 'coroutine'>
print(coro)         # <coroutine object say_hello at 0x...>

# Now actually run it
result = asyncio.run(say_hello())
print(result)       # 42
```

**Goal:** Burn into memory that `async def` changes calling semantics.

---

### Exercise 2 — `time.sleep` vs `asyncio.sleep`

Run both versions from the `asyncio.sleep` section above. Confirm:
- `time.sleep` version takes ~6s
- `asyncio.sleep` version takes ~2s

Then modify the async version to run 10 tasks with random delays between 1–3 seconds. What's the total time?

```python
import asyncio
import time
import random

async def task(name):
    delay = random.uniform(1, 3)
    print(f"{name}: sleeping {delay:.1f}s")
    await asyncio.sleep(delay)
    print(f"{name}: done")
    return delay

async def main():
    tasks = [task(f"T{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)
    print(f"Max individual delay: {max(results):.1f}s")

start = time.perf_counter()
asyncio.run(main())
print(f"Total wall time: {time.perf_counter() - start:.1f}s")
```

**Expected:** Total wall time ≈ the longest single delay, not the sum of all delays.

---

### Exercise 3 — Build a simple timer

Write a coroutine that acts as a countdown timer, printing each second.

```python
import asyncio
import time

async def countdown(name, seconds):
    for remaining in range(seconds, 0, -1):
        print(f"[{name}] {remaining}s remaining")
        await asyncio.sleep(1)
    print(f"[{name}] Done!")

async def main():
    # Run two timers concurrently
    await asyncio.gather(
        countdown("Timer A", 5),
        countdown("Timer B", 3),
    )

asyncio.run(main())
```

**Expected output:** Both timers interleave their prints. Timer B finishes first while Timer A keeps going.

**Extension:** Add a third coroutine that prints "heartbeat" every 0.5 seconds. Observe that it interleaves with both timers.

---

### Exercise 4 — Chain coroutines

Build a small async pipeline where each stage awaits the previous.

```python
import asyncio

async def fetch_data(source):
    print(f"  Fetching from {source}...")
    await asyncio.sleep(0.5)   # simulate network
    return {"source": source, "value": 42}

async def transform(data):
    print(f"  Transforming {data}...")
    await asyncio.sleep(0.2)   # simulate processing
    return {**data, "value": data["value"] * 2}

async def save(data):
    print(f"  Saving {data}...")
    await asyncio.sleep(0.1)   # simulate disk write
    return True

async def pipeline(source):
    raw = await fetch_data(source)
    processed = await transform(raw)
    success = await save(processed)
    return success

async def main():
    result = await pipeline("api.example.com")
    print(f"Pipeline completed: {result}")

asyncio.run(main())
```

**Goal:** Get comfortable with chains of `await` across multiple coroutines.

---

### Exercise 5 — Spot the blocking call

Each function below has a bug. Identify what's wrong and fix it.

```python
import asyncio
import time

# Bug 1: accidentally blocking
async def slow_operation():
    time.sleep(2)     # bug: blocks the entire event loop
    return "done"

# Bug 2: forgetting await
async def get_value():
    return 100

async def main_buggy():
    value = get_value()    # bug: returns coroutine, not 100
    print(value + 1)       # TypeError

# Bug 3: calling asyncio.run inside a coroutine
async def inner():
    return "inner result"

async def outer():
    result = asyncio.run(inner())  # bug: event loop already running
    print(result)
```

Fix all three, then write a test that confirms each fixed version works correctly.

---

### Challenge — Async workflow with timing

Build a coroutine that simulates processing a list of "jobs". Each job has a name and a duration. Run all jobs concurrently and print a summary when they're all done.

Requirements:
- Each job prints when it starts and when it finishes
- The summary shows total wall time and each job's duration
- Use `asyncio.gather` to run them concurrently

```python
import asyncio
import time

JOBS = [
    ("parse-logs",     1.2),
    ("send-email",     0.8),
    ("resize-images",  2.1),
    ("update-db",      0.5),
    ("generate-report",1.7),
]

async def run_job(name, duration):
    # your implementation here
    ...

async def main():
    # your implementation here
    ...

asyncio.run(main())
```

**Expected total time:** ~2.1s (the longest single job), not the sum (~6.3s).

---

## What's Next

You can write and chain coroutines. But so far you've only awaited them sequentially — one after another. In **section 2.2** you'll learn about the event loop itself: how it schedules work, how to create tasks that run *truly concurrently*, and what's actually happening under the hood when you call `asyncio.run()`.
