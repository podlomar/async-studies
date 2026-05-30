# Asyncio Mastery — A Hands-On Curriculum (Python 3.12)

A practical, exercise-driven path to a *deep* understanding of Python's `asyncio`,
with a light backend-fundamentals brush-up woven in. Built for someone coming from
frontend development who wants the mental model, not just the syntax.

- **Target:** Python 3.12 on Linux/Ubuntu
- **Libraries:** standard library + small utility libs only (`requests`, optionally `httpx`). **No web frameworks.**
- **Mix:** ~80% asyncio, ~20% general backend (interview-flavored)
- **Format per topic:** *Build* (hands-on) → *Diagnose* (read code / find the bug) → *Stretch* (extra)

> This file is both a **study plan** and a **generation spec**. Each section is written so you can
> ask Claude Code to expand it into real exercise files inside your repo. See *How to use this with Claude Code* below.

---

## Suggested repo layout

```
asyncio-lab/
├── CLAUDE.md                 # conventions (paste the block below)
├── asyncio-curriculum.md     # this file — the master plan
├── exercises/
│   ├── 01-coroutines-loop/
│   │   ├── README.md         # problem statements + hints (generated)
│   │   ├── build_starter.py  # TODO skeleton, no solution
│   │   ├── diagnose.py       # buggy/tricky snippet to reason about
│   │   ├── solution/         # kept separate so you don't peek
│   │   └── test_build.py     # unittest.IsolatedAsyncioTestCase
│   ├── 02-gather-tasks/
│   └── ...
└── backend-sidequests/
    ├── http-semantics.md
    ├── sqlite-persistence/
    └── ...
```

---

## Global concepts & the one mental model to anchor everything

Before the sections, internalize this — it explains 90% of asyncio surprises:

1. **A coroutine is lazy.** Calling `async def f()` *returns a coroutine object and runs nothing*.
   (Coming from JS this is the big inversion: a JS `Promise` starts executing immediately; a Python
   coroutine does nothing until you `await` it or schedule it as a Task.)
2. **One thread, one loop, cooperative scheduling.** The event loop runs one coroutine at a time.
   Control only moves to another coroutine at an `await` that actually suspends (e.g. `await asyncio.sleep`,
   network IO). Between `await`s your code is effectively single-threaded and uninterruptible.
3. **`await` ≠ concurrency.** `await foo()` *waits*. To run things at the same time you must create
   Tasks (`create_task`, `gather`, `TaskGroup`) so they're all scheduled on the loop together.
4. **Blocking the thread blocks *everything*.** A synchronous CPU loop or `time.sleep` or `requests.get`
   stalls the entire loop — every other coroutine freezes. This is the #1 real-world async bug.

Keep these four in mind and most "why didn't this run concurrently?" / "why did everything freeze?"
moments become obvious.

---

# The Asyncio Spine (Sections 1–11)

Each section below gives Claude Code enough to generate a full lesson: the mental model, the concepts/gotchas
to cover, Python 3.12 notes, the three exercises (with hints), and the backend tie-in.

---

## Section 1 — Coroutines & the event loop

**Mental model / why it matters:** This is where you feel that coroutines are lazy and that one loop runs
the show. Get this wrong and nothing else makes sense.

**Concepts to internalize**
- `async def`, `await`, coroutine objects vs. running coroutines.
- `asyncio.run()` creates a loop, runs the top coroutine, then closes the loop.
- `await asyncio.sleep(x)` *yields control* back to the loop (unlike `time.sleep`, which doesn't).
- The "coroutine was never awaited" `RuntimeWarning` and what causes it.

**Python 3.12 note:** Prefer `asyncio.run`; avoid `asyncio.get_event_loop()` (its implicit-loop behavior
is deprecated). Mention `asyncio.Runner` as the lower-level primitive `run` wraps.

**Exercises**
- **Build — "Staggered greeter / fake downloader":** Write 3 coroutines that `await asyncio.sleep`
  for different durations and print start/finish. Run them *sequentially* first (await one after another),
  observe total time = sum. *Hint: time it with `time.perf_counter()`; this is the baseline you'll beat in Section 2.*
- **Diagnose:** A snippet that does `result = fetch_data()` (no `await`) and then prints `result`, getting
  `<coroutine object ...>`. *Hint to give the learner: what type is `result`? What warning appears at exit, and why?*
- **Stretch:** Implement a 20-line toy "event loop": a list of `(ready_at, callback)` tuples you pop and run
  in time order. Goal: see that "the loop" is just a scheduler, not magic.

**Backend tie-in (interview):** The three concurrency models — **processes vs. threads vs. async** — and when
each wins. One-liner to be able to say: *async is best for high-concurrency IO-bound work in a single process;
threads for blocking IO you can't make async; processes for CPU-bound work.*

---

## Section 2 — Running things concurrently (`create_task`, `gather`)

**Mental model:** Concurrency requires *scheduling multiple things on the loop at once*. `await` in a loop
is still serial.

**Concepts**
- `asyncio.create_task(coro)` schedules a coroutine to run on the loop *now* and returns a `Task`.
- `asyncio.gather(*coros)` schedules all and waits for all; returns results in order.
- The fire-and-forget gotcha: a Task with no saved reference can be garbage-collected mid-flight.
- `return_exceptions=True` vs. the default fail-on-first-exception behavior of `gather`.

**Exercises**
- **Build — "Concurrent fetcher":** Fetch N endpoints concurrently and compare wall-clock time vs. the
  serial Section 1 version. *Use `asyncio.to_thread(requests.get, url)` here* (since `requests` is blocking),
  and note in the README that we'll meet a real async client in Section 8/9. *Hint: `gather` preserves order.*
- **Diagnose:** A `for url in urls: results.append(await fetch(url))` loop the author *thinks* is concurrent.
  *Questions for learner: how many requests are in flight at any moment? How would you fix it with `create_task`/`gather`?*
  Bonus snippet: `asyncio.create_task(worker())` with no saved reference — why might it never finish?
- **Stretch:** Use `gather(..., return_exceptions=True)` where one task raises. Inspect the returned list and
  explain what you get vs. the default behavior.

**Backend tie-in:** **Fan-out / fan-in**, and **latency vs. throughput** — concurrency hides latency; it doesn't
make a single request faster.

---

## Section 3 — Awaitables, Futures & escaping to threads (`to_thread`, executors)

**Mental model:** Not everything is a coroutine. `Future` is the low-level "result that will exist later."
Blocking work belongs *off* the loop.

**Concepts**
- The trio: **coroutine** (what you `async def`), **Task** (a scheduled coroutine), **Future** (a pending result).
- `loop.run_in_executor(None, blocking_fn, *args)` and the friendlier `asyncio.to_thread(blocking_fn, *args)`.
- Creating and resolving a raw `Future` manually (to understand callbacks-meet-await).

**Exercises**
- **Build — "Don't freeze the server":** A coroutine must call a blocking function (simulate with
  `time.sleep` or a CPU loop). Make it not block the loop using `asyncio.to_thread`, and prove other coroutines
  keep running meanwhile (e.g. a heartbeat printer). *Hint: run the heartbeat as a separate Task.*
- **Diagnose:** Code with a hidden `time.sleep(2)` inside an otherwise-async pipeline; the "heartbeat" Task
  stops ticking for 2s. *Questions: which line froze the loop? Why doesn't `await` help here? Two ways to fix.*
- **Stretch:** Create a `loop.create_future()`, hand it to a `loop.call_later(...)` callback that sets its result,
  and `await` it. You've just bridged callback-world and await-world by hand.

**Backend tie-in (interview heavyweight):** **The GIL.** Why threads help IO-bound but not CPU-bound work,
and why CPU-bound needs `multiprocessing`. Note: 3.12 still has the GIL; the free-threaded build is an
*experimental* 3.13+ thing — good to mention to show you track the ecosystem.

---

## Section 4 — Cancellation & timeouts

**Mental model:** Cancellation is delivered as an exception (`CancelledError`) at the next suspension point.
Cleanup must be deliberate.

**Concepts**
- `task.cancel()`, and `CancelledError` (a `BaseException`, so bare `except Exception` won't catch it — by design).
- `async with asyncio.timeout(seconds):` (3.11+) and the older `asyncio.wait_for`.
- `asyncio.shield` to protect a critical region from cancellation.
- Cleanup in `try/finally`; why a long-running task should periodically be cancellable.

**Exercises**
- **Build — "First response wins":** Launch several "mirror" lookups (different simulated latencies), take the
  fastest result, and cancel the losers. Then wrap a slow op in `asyncio.timeout`. *Hint: `asyncio.wait(..., return_when=FIRST_COMPLETED)` is one route.*
- **Diagnose:** A worker that does `try: ... except Exception: pass` around its loop and therefore *cannot be
  cancelled*. *Questions: why does `.cancel()` seem ignored? What's special about `CancelledError`'s base class? Where should cleanup go?*
- **Stretch:** Show the difference between cancelling a `shield`-ed coroutine vs. an unshielded one.

**Backend tie-in:** **Retries with exponential backoff + jitter**, request **deadlines/SLAs**, and the concept
behind a **circuit breaker**.

---

## Section 5 — Synchronization primitives & `Queue`

**Mental model:** Even single-threaded, you get races *across `await` boundaries*. Primitives coordinate
cooperative tasks; queues decouple producers from consumers.

**Concepts**
- `asyncio.Lock`, `Semaphore`, `Event`, `Condition` — and why you must use the `asyncio` versions, not `threading` ones.
- `asyncio.Queue` for producer/consumer and backpressure (bounded `maxsize`).
- Check-then-act races that appear when an `await` sits between the check and the act.

**Exercises**
- **Build — "Rate-limited API caller":** Use a `Semaphore(5)` to cap concurrency while firing 50 simulated
  API calls. (Directly analogous to throttling concurrent calls to any rate-limited service.) Then build a
  **producer/consumer**: a producer puts jobs on an `asyncio.Queue`, M worker tasks consume them. *Hint: use
  sentinel values or `queue.join()` + `task_done()` for clean shutdown.*
- **Diagnose:** A counter incremented as `tmp = counter; await something(); counter = tmp + 1` across tasks —
  a lost-update race. Or a snippet using `threading.Lock` in async code. *Questions: where's the race window?
  Why is the `threading` primitive wrong here?*
- **Stretch:** Build a bounded worker pool with backpressure: when the queue is full, producers must wait.
  Observe how `maxsize` shapes throughput. (This is the hand-built core of what a job queue like BullMQ does.)

**Backend tie-in:** **Rate limiting, backpressure, idempotency, worker pools** — the conceptual foundation of
background job processing.

---

## Section 6 — Structured concurrency: `TaskGroup` & exception groups (3.11+)

**Mental model:** A `TaskGroup` owns its children: if one fails, the rest are cancelled and errors surface
together. This is the modern default.

**Concepts**
- `async with asyncio.TaskGroup() as tg: tg.create_task(...)`.
- How a child exception cancels siblings and raises an `ExceptionGroup`.
- `except*` syntax to handle grouped exceptions by type.
- When you still want `gather` (best-effort, collect-all-results) vs. `TaskGroup` (fail-fast, all-or-nothing).

**Exercises**
- **Build:** Re-implement the Section 2 fetcher with `TaskGroup`, then deliberately make one task fail and
  watch the siblings get cancelled. *Hint: log each task's entry/exit to *see* the cancellation.*
- **Diagnose:** Code expecting `gather`-style partial results from a `TaskGroup`, surprised by an
  `ExceptionGroup`. *Questions: what type is raised? How many tasks finished? How do you handle two different
  failure types with `except*`?*
- **Stretch:** Write the same "fan-out with one failure" two ways — `gather(return_exceptions=True)` vs.
  `TaskGroup` — and write down the trade-off in one paragraph.

**Backend tie-in:** **Fail-fast vs. best-effort** semantics, and how partial failures propagate in a fan-out
(very relevant to multi-call pipelines).

---

## Section 7 — Async iteration & context managers

**Mental model:** `async for` and `async with` exist because *producing the next item* or *acquiring/releasing
a resource* may itself need to await.

**Concepts**
- `__aiter__`/`__anext__`, `async for`, and `async` generators (`async def` with `yield`).
- `__aenter__`/`__aexit__`, `async with`, and `@contextlib.asynccontextmanager`.
- Why async generators need careful closing (`aclose`) and what `contextlib.aclosing` is for.

**Exercises**
- **Build — "Streaming chunks":** An async generator that yields chunks over time (simulating a streaming
  response from a transcription/LLM endpoint), consumed with `async for`. Add an async context manager that
  "opens" and "closes" a fake connection around the stream. *Hint: `@asynccontextmanager` is the easy path.*
- **Diagnose:** Someone using a plain `for`/sync generator where `async for` is required (or forgetting `await`
  in `__anext__`). Plus an async generator that's abandoned mid-iteration and leaks. *Questions: what error/warning
  appears? How does `aclosing` help?*
- **Stretch:** Implement an async generator with **backpressure** — it only produces the next chunk when the
  consumer is ready, and pages results (like cursor-based pagination).

**Backend tie-in:** **Streaming responses & pagination**, and **resource lifecycle** (acquire/release safely).

---

## Section 8 — Don't block the loop: blocking vs. async, IO-bound vs. CPU-bound

**Mental model:** The loop's worst enemy is synchronous work. Route blocking IO to threads, CPU work to processes.

**Concepts**
- Spotting blocking calls: `time.sleep`, `requests`, blocking file IO, heavy pure-Python loops.
- `asyncio.to_thread` / `run_in_executor` (thread pool) for blocking IO; `ProcessPoolExecutor` for CPU-bound.
- `asyncio` **debug mode** and the "slow callback" warning to *detect* blocking automatically.

**Exercises**
- **Build — "Mixed workload router":** Given a workload mixing async IO, a blocking IO call (`requests`), and a
  CPU-bound function, route each to the right place and keep a heartbeat alive throughout. *Hint: thread pool for
  the blocking IO, process pool for the CPU work.*
- **Diagnose:** A "concurrent" server-ish program that can't actually serve concurrently because one synchronous
  DB/file call blocks the loop. *Questions: which call is the culprit? How do you confirm it with debug mode?*
- **Stretch:** Turn on `asyncio.run(main(), debug=True)` (or `PYTHONASYNCIODEBUG=1`), trigger a slow callback,
  and read the warning. Then compare `ThreadPoolExecutor` vs. `ProcessPoolExecutor` timings on a CPU task to
  *see* the GIL.

**Backend tie-in:** **Connection/thread pools**, and watching the **GIL** bite in practice.

---

## Section 9 — Streams & networking (the big FE→BE bridge)

**Mental model:** Under every web framework is a socket reading bytes and writing bytes. Building this once
demystifies the whole stack.

**Concepts**
- `asyncio.start_server` / `asyncio.open_connection`, `StreamReader` / `StreamWriter`.
- `await writer.drain()` (backpressure) and properly closing connections (`writer.close()` + `await writer.wait_closed()`).
- Framing: how you know where one message ends (newline-delimited, length-prefixed).

**Exercises**
- **Build — "TCP echo → tiny HTTP server":** First a TCP echo server + client. Then parse a raw HTTP request
  line + headers off the socket and write back a valid `HTTP/1.1 200 OK` response by hand. *Hint: read until `\r\n\r\n`
  for headers; you now see what a framework hides.* Bonus: a concurrent port scanner.
- **Diagnose:** A server that never calls `await writer.drain()` (or never closes the writer). *Questions: what
  happens under load / with a slow client? Why does the connection sometimes hang?*
- **Stretch:** A line-based chat server that broadcasts each client's message to all others (a shared set of writers).

**Backend tie-in:** **HTTP from sockets up** — the request/response cycle, status codes, headers — exactly what
a frontend dev usually consumes but rarely serves.

---

## Section 10 — Subprocesses

**Mental model:** Talking to external programs without blocking the loop, and reading their output as it streams.

**Concepts**
- `asyncio.create_subprocess_exec` (argument list, safe) vs. `create_subprocess_shell` (shell string, injection risk).
- `await proc.communicate()` to avoid pipe deadlocks; streaming `stdout` line-by-line.
- Environment, working directory, exit codes.

**Exercises**
- **Build — "Concurrent command fan-out":** Run several shell commands concurrently (e.g. `wc -l` on files, or
  probing media files) and collect their outputs and exit codes. *Hint: gather/`TaskGroup` over subprocess coroutines.*
- **Diagnose:** A subprocess that deadlocks because the code writes to/reads from pipes manually instead of using
  `communicate()`. *Questions: why does it hang on large output? What does `communicate` do for you?*
- **Stretch:** Stream a long-running process's stdout line-by-line and react to lines as they arrive.

**Backend tie-in:** **Shelling out safely** — `exec` vs. `shell`, **shell-injection** risk, environment handling.

---

## Section 11 — Patterns, graceful shutdown & debugging

**Mental model:** Real services start, run many tasks, and must stop *cleanly* — draining work, cancelling tasks,
closing resources — when a signal arrives.

**Concepts**
- `loop.add_signal_handler` for SIGINT/SIGTERM; orchestrating a clean shutdown.
- Cancelling pending tasks at exit; the "Task was destroyed but it is pending!" warning and its cause.
- Health checks, structured `logging` (not `print`), and 3.12's `asyncio.eager_task_factory` as an optimization knob.

**Exercises**
- **Build — "Mini job processor":** Combine everything — a bounded `Queue`, a pool of worker Tasks, per-job
  `timeout`, and graceful shutdown on Ctrl-C that finishes in-flight jobs then exits cleanly. *Hint: catch the
  signal, stop accepting new work, `await` the queue drain, then cancel workers.*
- **Diagnose:** A program that exits with "Task was destroyed but it is pending!" warnings. *Questions: which
  tasks were orphaned? How do you collect and cancel them before the loop closes?*
- **Stretch:** Add structured logging of each task's lifecycle, then experiment with
  `loop.set_task_factory(asyncio.eager_task_factory)` (3.12) and describe what changes about *when* tasks start running.

**Backend tie-in:** **Graceful shutdown, signals, health checks, and proper logging** — the operational basics
every backend service needs.

---

# Backend side-quests (layer in between asyncio sections)

Short, framework-free, interview-relevant. Generate each as its own folder/README when you want a change of pace.

### A. HTTP semantics drill
Methods (GET/POST/PUT/PATCH/DELETE), **safe vs. idempotent**, status code families and key codes
(200/201/204/301/302/304/400/401/403/404/409/422/429/500/503), caching headers (`ETag`, `Cache-Control`),
and REST basics. *Exercise idea: given a set of operations, choose the correct method + status code and justify.*

### B. Persistence with `sqlite3` (stdlib)
CRUD, **transactions/ACID**, what an **index** does to query speed, and the **N+1 query** problem.
*Async tie-in:* `sqlite3` is blocking, so wrapping it in `asyncio.to_thread` is a perfect callback to Section 8.
*Exercise idea: build a tiny "jobs" table, insert/query/update inside a transaction, then add an index and measure.*

### C. `logging` & configuration
Structured logging, log levels, handlers/formatters vs. `print`; config via environment variables (12-factor),
and keeping secrets out of code. *Exercise idea: convert a `print`-debugged script to leveled logging with a JSON formatter.*

### D. Testing async code (stdlib)
`unittest.IsolatedAsyncioTestCase` — write `async def test_...` methods, `await` your coroutines, and assert.
*Exercise idea: write tests for your Section 5 rate limiter (assert max concurrency never exceeds N).*

---

# Suggested pacing

- **Foundations (don't rush):** Sections 1–5. This is where the mental model is forged.
- **Modern core:** Section 6 (`TaskGroup`) — treat as essential, not advanced; it's the recommended default in 3.12.
- **Going real:** Sections 7–11. By the end you'll have built a streaming generator, a raw HTTP server, and a
  job processor — concrete, demonstrable backend artifacts.
- Slot side-quests A–D wherever a context-switch helps (A early, B around Section 8, C/D anytime).

# Self-assessment checklist (you "get" asyncio when you can…)

- [ ] Explain why a coroutine doesn't run until awaited/scheduled, and predict the "never awaited" warning.
- [ ] Convert a serial `await` loop into genuine concurrency three ways (`gather`, `create_task`, `TaskGroup`).
- [ ] Identify a loop-blocking call in unfamiliar code and fix it with `to_thread` or a process pool.
- [ ] Cancel tasks correctly and explain why `CancelledError` is a `BaseException`.
- [ ] Choose `TaskGroup` vs. `gather` for a given failure requirement and defend the choice.
- [ ] Build a bounded producer/consumer with clean shutdown from memory.
- [ ] Write a raw async TCP/HTTP handler and explain what a framework abstracts away.
- [ ] Articulate processes vs. threads vs. async and the GIL's role — interview-ready.
