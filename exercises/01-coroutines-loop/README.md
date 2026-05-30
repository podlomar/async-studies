# Section 1 — Coroutines & the event loop

## Concepts to understand first

Read through these pointers and make sure each one makes intuitive sense *before* you write code.
The exercises will feel confusing otherwise.

**Coroutines are lazy.**
Calling `async def f()` returns a coroutine object; it does not execute one line of the body.
The body only runs when you `await` the coroutine, or schedule it as a `Task`.
This is the opposite of a JavaScript Promise, which starts executing immediately on creation.

**One thread. One loop. Cooperative scheduling.**
`asyncio.run(main())` creates an event loop, hands control to `main`, and keeps driving the loop
until `main` returns. While `main` runs, it is the *only* thing running in that thread.
Control moves to another coroutine only at an `await` that actually suspends — for example
`await asyncio.sleep(...)` yields back to the loop; `time.sleep(...)` (no await, no yield) does not.

**`await` means "wait for this", not "run this concurrently".**
`await some_coroutine()` runs that coroutine to completion before the next line executes.
Concurrency requires scheduling multiple things on the loop at once — that's Section 2.

**`asyncio.run` vs `asyncio.get_event_loop`.**
In Python 3.12, always use `asyncio.run(main())` as the entry point.
`asyncio.get_event_loop()` has deprecated implicit-loop semantics and should be avoided.
Under the hood, `asyncio.run` is a thin wrapper around `asyncio.Runner`, the lower-level primitive.

---

## Build exercise — "Staggered greeter / fake downloader"

### Scenario

You are writing a backend utility that simulates downloading three files from different servers.
Each "download" is represented by a coroutine that prints a start message, waits for a fake
network delay, then prints a finish message with elapsed time.

### What to build

Open `build_starter.py`.  Fill in all `TODO` blocks.

1. Write three coroutines — `download_small`, `download_medium`, `download_large` — each taking a
   `name: str` argument.  Each coroutine should:
   - Record the start time with `time.perf_counter()`.
   - Print `"[name] starting download..."`.
   - `await asyncio.sleep(...)` for a delay of your choosing (suggest 0.3 s, 0.7 s, 1.2 s).
   - Print `"[name] done in X.XXs"` using the elapsed time.

2. Write a `main()` coroutine that calls each of the three download coroutines **sequentially**
   (one `await` after another).  Measure total elapsed time and print it.

3. Observe that the total time is (approximately) the *sum* of the individual delays.
   Leave a comment explaining *why*.

### Expected output (approximate)

```
[small.csv] starting download...
[small.csv] done in 0.30s
[medium.csv] starting download...
[medium.csv] done in 0.70s
[large.csv] starting download...
[large.csv] done in 1.20s
Total time: 2.20s
```

### Hints

- The total time being the sum is the key insight: sequential `await` is still serial.
  You are not getting any concurrency. That baseline is what Section 2 will beat.
- `time.perf_counter()` returns a float of seconds with sub-millisecond precision.
- You do not need any imports beyond `asyncio` and `time`.

---

## Diagnose exercise

Open `diagnose.py`.  **Read it carefully and answer the questions in the comment block at the top
*before* running it.**  Then run it, observe the output and any warnings, and compare with your
predictions.

The snippet calls an `async def` function without `await` and assigns the return value to a
variable, then tries to use it.

Key questions (they are repeated inside the file):

1. What Python type is `result` at the point of the `print`?
2. What does the printed line actually show?
3. What warning (if any) appears after the program exits, and which part of the code causes it?
4. How would you fix the code so it correctly fetches and prints the payload?

---

## Stretch exercise — Toy event loop

This exercise has no starter file.  Write it from scratch in a new file, e.g. `stretch_loop.py`.

### Goal

Implement a ~20-line toy "event loop" to see that an event loop is just a scheduler — not magic.

### Spec

```python
import time

def toy_event_loop(tasks):
    """
    tasks: list of (ready_at: float, callback: callable)
           where ready_at is time.time() + delay.
    Runs until all tasks have fired.
    """
    # TODO: implement
    ...
```

Rules and constraints:

- Store tasks as a list of `(ready_at, callback)` tuples (already sorted or sort inside the loop).
- Each iteration of the loop: find the task with the smallest `ready_at`; if it is due
  (`ready_at <= time.time()`), call its callback and remove it from the list; otherwise
  `time.sleep` until it is due (this is the "poll / sleep" kernel of a real loop).
- After calling a callback, the callback may *enqueue new tasks* by returning a list of
  `(delay, callback)` pairs.  Add those to the task list.
- Stop when the task list is empty.

### What to observe

Run a handful of callbacks scheduled at different delays and see them execute in time order
regardless of the order you added them.  Then notice how `asyncio.sleep` would be the async
equivalent of "schedule this callback for the future."

### Why this matters

Python's real event loop does the same thing at its core — it maintains a heap of ready-at
timestamps, checks for IO readiness via `select`/`epoll`, and dispatches callbacks.
`await asyncio.sleep(x)` is syntactic sugar for "schedule the continuation of this coroutine
at `now + x` and yield back to the loop."

---

## Backend tie-in — Processes vs. threads vs. async

Know this cold for interviews:

| Model | Best for | Why |
|---|---|---|
| `multiprocessing` | CPU-bound work | Each process has its own GIL; true parallelism |
| `threading` | Blocking IO you cannot make async | Threads release the GIL on IO syscalls |
| `asyncio` | High-concurrency IO-bound work | One thread, no context-switch overhead, scales to thousands of concurrent operations |

One-liner to say aloud: *"Async is best for high-concurrency IO-bound work in a single process.
Use threads for blocking IO you can't make async. Use processes for CPU-bound work."*

Note on Python 3.12: the GIL is still present in the stable release. The free-threaded build
is an experimental 3.13+ option — mentioning that you track this shows ecosystem awareness.
