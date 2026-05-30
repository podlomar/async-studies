# 2.2 The Event Loop

> **Phase 2 — Asyncio Fundamentals**
>
> You can write coroutines and chain them with `await`. Now learn what actually runs them — the event loop — and how it decides what executes when.

---

## What the Event Loop Does

The **event loop** is the engine at the centre of every asyncio program. Its job is simple to state:

> Run coroutines one step at a time. When one yields, run another. When I/O completes, wake up whoever was waiting for it.

Everything else in `asyncio` — tasks, futures, `gather`, timeouts — is built on top of this single loop.

The loop runs in one thread. It never truly runs two coroutines at the same moment. Instead, it switches between them so fast that from the outside it looks concurrent.

### The loop's main cycle

```
Loop iteration:
1. Poll the OS: which I/O events have completed? (read ready, write ready, timer fired)
2. For each completed event → mark the waiting coroutine as ready
3. Run every coroutine in the ready queue until it yields (hits an await)
4. Go back to 1
```

Step 1 uses the OS's I/O multiplexing interface — `epoll` on Linux, `kqueue` on macOS, `IOCP` on Windows. The loop can watch thousands of file descriptors simultaneously while blocking only as long as there is nothing ready to run.

```
         ┌─────────────────────────────────────┐
         │             Event Loop              │
         │                                     │
         │  ┌──────────┐    ┌───────────────┐  │
         │  │  Ready   │───▶│  Run one step │  │
         │  │  Queue   │◀──┐│  of a coro   │  │
         │  └──────────┘   ││               │  │
         │                 │└───────────────┘  │
         │  ┌──────────┐   │        │ hits     │
         │  │ I/O poll │   │        │ await    │
         │  │ (epoll)  │───┘        ▼          │
         │  └──────────┘   ┌───────────────┐   │
         │       ▲         │  Suspended    │   │
         │       │         │  coroutines   │   │
         │  OS notifies    └───────────────┘   │
         └─────────────────────────────────────┘
```

---

## Lifecycle of a Coroutine

A coroutine object moves through a set of states during its lifetime.

```
           call async def fn()
                   │
                   ▼
             ┌──────────┐
             │  Created │  ← coroutine object exists, body not started
             └──────────┘
                   │  awaited or wrapped in a Task
                   ▼
             ┌──────────┐
          ┌─▶│ Running  │  ← event loop is executing this coroutine right now
          │  └──────────┘
          │        │  hits await
          │        ▼
          │  ┌──────────┐
          │  │Suspended │  ← waiting for I/O, sleep, or another coroutine
          │  └──────────┘
          │        │  awaitable completes
          └────────┘
                   │  body finishes
                   ▼
             ┌──────────┐
             │   Done   │  ← result (or exception) available
             └──────────┘
```

A coroutine that is never awaited stays in *Created* state forever and its body never runs. Python will warn you about this:

```python
import asyncio

async def hello():
    return "hi"

coro = hello()   # Created — not awaited
# RuntimeWarning: coroutine 'hello' was never awaited
```

---

## `asyncio.run()`

`asyncio.run(coro)` is the standard entry point. It:

1. Creates a brand-new event loop
2. Runs `coro` on it until the coroutine returns
3. Cancels any remaining tasks
4. Closes the loop

```python
import asyncio

async def main():
    print("running inside the event loop")
    await asyncio.sleep(0)
    print("still running")

asyncio.run(main())
```

Important: `asyncio.run()` is for the *top level only*. If the loop is already running (you're inside an async function), calling `asyncio.run()` again raises:

```
RuntimeError: This event loop is already running.
```

Inside async code, always use `await` to call other coroutines.

---

## `asyncio.get_running_loop()`

From inside a coroutine, you can get a reference to the currently running loop:

```python
import asyncio

async def inspect_loop():
    loop = asyncio.get_running_loop()
    print(f"loop: {loop}")
    print(f"running: {loop.is_running()}")
    print(f"time: {loop.time():.3f}")   # monotonic clock used by the loop

asyncio.run(inspect_loop())
```

`loop.time()` returns the loop's internal monotonic clock — used for scheduling timers. It's not wall-clock time; it's a counter that only goes forward.

### `get_running_loop()` vs `get_event_loop()`

You'll see both in older code.

| Function | Behaviour |
|---|---|
| `asyncio.get_running_loop()` | Returns the running loop. Raises `RuntimeError` if none. Preferred. |
| `asyncio.get_event_loop()` | Returns the running loop, or creates and sets a new one if none exists. Deprecated pattern. |

Use `get_running_loop()` in new code. If you need the loop from a sync context (e.g. a callback), pass it explicitly rather than calling `get_event_loop()`.

---

## The Ready Queue

The event loop maintains a **ready queue** — a list of callbacks and coroutine steps waiting to run. When you create a task, the loop puts it in the ready queue. Each iteration of the loop drains the queue, running every item once until it yields.

```python
import asyncio

async def show_order():
    print("A: before first yield")
    await asyncio.sleep(0)      # yield to loop — go to back of queue
    print("A: after first yield")
    await asyncio.sleep(0)
    print("A: after second yield")

async def other():
    print("B: running")
    await asyncio.sleep(0)
    print("B: resuming")

async def main():
    await asyncio.gather(show_order(), other())

asyncio.run(main())
```

Output:
```
A: before first yield
B: running
A: after first yield
B: resuming
A: after second yield
```

Each `await asyncio.sleep(0)` puts the coroutine to the back of the ready queue. The other coroutine gets a turn in between. This is cooperative scheduling made visible.

---

## Task Scheduling

A **Task** wraps a coroutine and schedules it to run on the event loop. Creating a task with `asyncio.create_task()` immediately puts the coroutine into the ready queue — it doesn't wait for you to `await` it.

```python
import asyncio

async def worker(name, delay):
    print(f"{name}: start")
    await asyncio.sleep(delay)
    print(f"{name}: done")
    return name

async def main():
    # Schedule both tasks — they enter the ready queue immediately
    task_a = asyncio.create_task(worker("A", 2))
    task_b = asyncio.create_task(worker("B", 1))

    print("tasks created, not yet running")

    # Now yield control so the loop can run them
    result_a = await task_a
    result_b = await task_b

    print(f"results: {result_a}, {result_b}")

asyncio.run(main())
```

Output:
```
tasks created, not yet running
A: start
B: start
B: done
A: done
results: A, B
```

Both tasks start before either finishes. Task B completes first (shorter delay) but `await task_a` still gets A's result correctly.

### `create_task` vs `await coro()`

```python
# Sequential — B doesn't start until A is done
await worker("A", 2)
await worker("B", 1)
# total: 3s

# Concurrent — A and B run at the same time
task_a = asyncio.create_task(worker("A", 2))
task_b = asyncio.create_task(worker("B", 1))
await task_a
await task_b
# total: 2s
```

`await coro()` runs a coroutine inline — the current coroutine suspends and waits for it to finish before moving on. `create_task(coro())` schedules it independently — both run concurrently.

---

## Observing Execution Order

The event loop processes tasks in the order they become ready. You can observe this by watching when coroutines wake up after sleeps.

```python
import asyncio
import time

start = time.perf_counter()

def ts():
    return f"{time.perf_counter() - start:.2f}s"

async def task(name, sleep_for):
    print(f"[{ts()}] {name}: sleeping {sleep_for}s")
    await asyncio.sleep(sleep_for)
    print(f"[{ts()}] {name}: awake")

async def main():
    await asyncio.gather(
        task("A", 1.0),
        task("B", 0.5),
        task("C", 1.5),
        task("D", 0.2),
    )

asyncio.run(main())
```

Output (approximate):
```
[0.00s] A: sleeping 1.0s
[0.00s] B: sleeping 0.5s
[0.00s] C: sleeping 1.5s
[0.00s] D: sleeping 0.2s
[0.20s] D: awake
[0.50s] B: awake
[1.00s] A: awake
[1.50s] C: awake
```

All four start at ~0s. They wake up exactly when their timer expires, in order of their delay — not in the order they were created. The loop woke each one as soon as the OS signalled that its timer had fired.

---

## Loop Policies

Asyncio uses a **policy** to determine how event loops are created and retrieved. The default policy varies by platform:

| Platform | Default policy |
|---|---|
| Linux / macOS | `DefaultEventLoopPolicy` |
| Windows | `WindowsSelectorEventLoopPolicy` (Python <3.12) |

You rarely need to touch policies directly. The main exception is switching to `uvloop` for higher throughput:

```python
import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
asyncio.run(main())  # now uses uvloop under the hood
```

`uvloop` is a drop-in replacement written in Cython on top of libuv (the same engine as Node.js). It can be 2–4x faster for I/O-heavy workloads. Leave it for Phase 4; understand the default loop first.

---

## What Blocks the Event Loop

Because the loop runs in a single thread, anything that blocks the thread blocks everything. The most common mistakes:

```python
import time
import asyncio

# Bad: blocks the OS thread, no other coroutine can run
async def bad():
    time.sleep(2)           # freezes the event loop for 2s
    data = open("big.csv").read()   # synchronous file I/O
    result = compute_heavy()       # CPU-intensive work

# Good: use async-native alternatives
async def good():
    await asyncio.sleep(2)
    async with aiofiles.open("big.csv") as f:   # async file I/O
        data = await f.read()
    result = await loop.run_in_executor(None, compute_heavy)  # offload CPU work
```

The rule: **the event loop thread must never wait**. If it has to wait, every coroutine in your program stops dead.

You can detect accidental blocking in development with:

```python
asyncio.run(main(), debug=True)
```

Debug mode logs a warning when a coroutine holds the thread for more than 100ms without yielding.

---

## Key Concepts Summary

**Event loop** — the scheduler that runs coroutines, polls for I/O completion, and fires timers. There is one loop per thread.

**Ready queue** — the list of coroutine steps waiting to execute. The loop drains this queue each iteration.

**Task** — a coroutine wrapped and scheduled on the loop. Created with `asyncio.create_task()`. Runs concurrently with other tasks.

**Task switching** — happens only at `await` points. The loop runs one coroutine until it yields, then picks the next ready one.

**Cooperative multitasking** — coroutines yield voluntarily. The loop never preempts them. A coroutine that never awaits blocks everything.

**`asyncio.run()`** — creates a loop, runs one top-level coroutine, cleans up. One call per program.

**`get_running_loop()`** — access the running loop from inside async code.

---

## Practice Exercises

### Exercise 1 — Observe the ready queue

Predict the output of the following program, then run it to check.

```python
import asyncio

async def a():
    print("a1")
    await asyncio.sleep(0)
    print("a2")
    await asyncio.sleep(0)
    print("a3")

async def b():
    print("b1")
    await asyncio.sleep(0)
    print("b2")

async def main():
    await asyncio.gather(a(), b())

asyncio.run(main())
```

Write down what you expect before running. Then explain *why* the output appears in that order.

---

### Exercise 2 — Sequential vs concurrent tasks

Implement the same work two ways and measure the difference.

```python
import asyncio
import time

async def slow_step(name, duration):
    print(f"  {name}: start")
    await asyncio.sleep(duration)
    print(f"  {name}: done")
    return duration

STEPS = [("fetch", 1.2), ("process", 0.8), ("save", 0.5)]

async def sequential():
    for name, dur in STEPS:
        await slow_step(name, dur)

async def concurrent():
    tasks = [asyncio.create_task(slow_step(name, dur)) for name, dur in STEPS]
    for t in tasks:
        await t

for label, fn in [("Sequential", sequential), ("Concurrent", concurrent)]:
    start = time.perf_counter()
    asyncio.run(fn())
    print(f"{label}: {time.perf_counter() - start:.2f}s\n")
```

**Expected:** Sequential ~2.5s, Concurrent ~1.2s.

**Goal:** Make the difference between `await coro()` and `create_task(coro())` concrete.

---

### Exercise 3 — Inspect the loop

Write a coroutine that prints information about the running event loop.

```python
import asyncio

async def loop_info():
    loop = asyncio.get_running_loop()
    print(f"Loop type:    {type(loop).__name__}")
    print(f"Is running:   {loop.is_running()}")
    print(f"Is closed:    {loop.is_closed()}")
    print(f"Loop time:    {loop.time():.6f}")
    await asyncio.sleep(0.1)
    print(f"Loop time +0.1s: {loop.time():.6f}")

asyncio.run(loop_info())
```

**Goal:** Demystify the loop object. Observe that `loop.time()` advances in real time.

---

### Exercise 4 — Execution ordering

Create 5 tasks with different sleep durations. Print each task's start and finish with a timestamp. Verify that tasks finish in order of their duration, not their creation order.

```python
import asyncio
import time

start_time = time.perf_counter()

def ts():
    return f"{time.perf_counter() - start_time:.2f}s"

async def timed_task(task_id, duration):
    print(f"[{ts()}] task {task_id}: starting (will take {duration}s)")
    await asyncio.sleep(duration)
    print(f"[{ts()}] task {task_id}: finished")
    return task_id

async def main():
    durations = [1.5, 0.3, 1.0, 0.7, 0.5]
    tasks = [asyncio.create_task(timed_task(i, d)) for i, d in enumerate(durations)]
    results = await asyncio.gather(*tasks)
    print(f"\nGather returned: {results}")
    print(f"Total time: {ts()}")

asyncio.run(main())
```

**Goal:** See that `gather` collects results in *creation order*, even though tasks complete in *duration order*.

---

### Exercise 5 — Detect blocking

Use debug mode to catch a deliberately blocking coroutine.

```python
import asyncio
import time

async def blocking_coroutine():
    print("about to block...")
    time.sleep(0.2)    # blocks the event loop — debug mode will warn
    print("unblocked")

async def harmless():
    await asyncio.sleep(0.05)
    print("harmless task ran")

async def main():
    await asyncio.gather(blocking_coroutine(), harmless())

asyncio.run(main(), debug=True)
```

Run this and observe the warning from debug mode. Then fix `blocking_coroutine` to use `await asyncio.sleep(0.2)` and confirm the warning disappears.

---

### Challenge — Build a simple task monitor

Write a coroutine that runs alongside a set of tasks and periodically reports how many are still running.

```python
import asyncio
import time

async def worker(task_id, duration):
    await asyncio.sleep(duration)
    return task_id

async def monitor(tasks, interval=0.3):
    while True:
        done = sum(1 for t in tasks if t.done())
        pending = len(tasks) - done
        print(f"  [monitor] {done} done, {pending} pending")
        if pending == 0:
            break
        await asyncio.sleep(interval)

async def main():
    durations = [1.0, 0.4, 1.5, 0.8, 1.2]
    tasks = [asyncio.create_task(worker(i, d)) for i, d in enumerate(durations)]
    await asyncio.gather(monitor(tasks), *tasks)

asyncio.run(main())
```

**Goal:** Understand that tasks run concurrently with your own coroutine, and that you can inspect their state via `task.done()`.

---

## What's Next

You understand how the event loop schedules work and why `create_task` enables true concurrency. In **section 2.3** you'll go deeper into Tasks and Futures: how to run many tasks at once with `gather` and `wait`, handle results as they arrive with `as_completed`, and understand what a `Future` actually is under the hood.
