# Section 2 — Running things concurrently (`create_task`, `gather`)

## Concepts to understand first

Read through these pointers carefully before writing any code.
The difference between "sequential" and "concurrent" is the entire point of this section.

**`await` in a loop is still serial.**
If you write `for url in urls: result = await fetch(url)`, only one request is in flight
at any moment. Each `await` suspends the current coroutine and waits for that single operation
to complete before moving on. The loop structure does not add any concurrency.

**Scheduling vs. awaiting.**
`asyncio.create_task(coro)` hands the coroutine to the event loop *right now* and returns a
`Task` object. The coroutine starts working in the background — the loop will run it whenever
it gets control. You can create many tasks before awaiting any of them, and they all make
progress concurrently.

**`asyncio.gather` fans out and fans in.**
`asyncio.gather(coro1, coro2, coro3)` wraps each coroutine in a task, waits for all of them,
and returns their results as a list **in the same order you passed the coroutines**, regardless
of which one finishes first. This is the fan-out / fan-in pattern.

**The fire-and-forget trap.**
`asyncio.create_task(worker())` creates a Task, but if you do not store the reference somewhere,
the garbage collector can destroy the Task object mid-flight — before the coroutine has finished.
Always keep a reference to every Task you create.

**`gather` failure modes.**
By default, if any coroutine passed to `gather` raises an exception, `gather` re-raises that
exception immediately (the other tasks keep running, but their results are lost). Pass
`return_exceptions=True` to collect exceptions as regular return values instead of propagating
them — this lets you inspect partial failures in the returned list.

**Fan-out / fan-in in backend systems.**
Concurrency hides latency; it does not make a single request faster. If each of 10 requests
takes 1 s, running them serially takes 10 s; running them concurrently takes ~1 s (wall clock).
The throughput — requests served — is the same either way; the latency — time to get all results
— shrinks dramatically.

---

## Build exercise — "Concurrent status checker"

### Scenario

You are writing a backend health-check utility for a microservices platform. The platform has
several service endpoints, each of which responds after a simulated network delay. Operations
need to check all of them and report a summary. Right now it runs serially (as in Section 1);
your job is to make it concurrent and prove that the wall-clock time collapses to roughly the
longest single delay instead of their sum.

Because `requests.get` is a blocking call that would stall the event loop, you must wrap it in
`asyncio.to_thread`. (In a production system you would use an async HTTP client like `httpx`
with `await client.get(...)` — you will meet that in Section 8/9. The pattern you learn here
transfers directly.)

### What to build

Open `build_starter.py`. Fill in every `TODO` block.

1. Implement `check_service(name, url, delay)` — a coroutine that:
   - Prints `"[name] checking..."`.
   - Calls `await asyncio.to_thread(requests.get, url)` to perform a real (but tiny)
     HTTP GET without blocking the event loop.
   - `await asyncio.sleep(delay)` to simulate additional processing time.
   - Prints `"[name] OK (X.XXs)"` with elapsed time and returns `(name, response.status_code)`.

2. Implement `check_all_serial(services)` — runs each service check with `await` inside a
   `for` loop. Measure and print total time. This is the Section 1 baseline.

3. Implement `check_all_concurrent(services)` — runs every check concurrently using
   `asyncio.gather`. Measure and print total time. The wall-clock total should be close
   to `max(delays)`, not `sum(delays)`.

4. In `main()`, run `check_all_serial` then `check_all_concurrent` on the same list of
   services and print a final comparison line showing both times.

### Expected output (approximate)

```
--- Serial ---
[auth] checking...
[auth] OK (0.30s)
[users] checking...
[users] OK (0.50s)
[orders] checking...
[orders] OK (0.80s)
[payments] checking...
[payments] OK (0.40s)
Serial total: 2.00s

--- Concurrent ---
[auth] checking...
[users] checking...
[orders] checking...
[payments] checking...
[payments] OK (0.40s)
[auth] OK (0.30s)
[users] OK (0.50s)
[orders] OK (0.80s)
Concurrent total: 0.81s

Speedup: 2.00s serial vs 0.81s concurrent
```

### Hints

- `asyncio.gather` preserves result order: `results[0]` corresponds to the first argument
  even if a later coroutine finished first.
- If you want to see tasks complete out of order, watch the print output — faster services
  print their "OK" line before slower ones.
- Use `https://httpbin.org/get` or any reliable public endpoint that returns 200. If you want
  no real network dependency, replace the `requests.get` call with a plain `asyncio.sleep`
  and a hardcoded status code — note the trade-off in a comment.
- To use `asyncio.to_thread` you only need Python 3.9+. It wraps the blocking call in a
  thread from the default `ThreadPoolExecutor` so the event loop remains free.

---

## Diagnose exercise

Open `diagnose.py`. **Read it carefully and answer every question in the comment block at the
top *before* running it.** Then run it, compare with your predictions, and re-read `diagnose.py`
with fresh eyes.

The file contains two separate snippets:

**Snippet A** — a `for url in urls` loop that the author believes is running requests
concurrently.

**Snippet B** — a `create_task` call whose reference is immediately discarded.

Key questions (they are repeated inside the file):

**Snippet A:**
1. How many requests are in flight at any one moment? One, or many?
2. How would the timing of this loop compare to a concurrent version?
3. How would you rewrite it to make all requests run concurrently?
   Write your answer (no code required — a one-sentence description is fine).

**Snippet B:**
4. `asyncio.create_task(background_job())` schedules a task. The next line immediately calls
   `await asyncio.sleep(0)`. Does the task always run to completion?
5. What has to happen for a Task to be garbage-collected mid-flight?
6. How would you fix the fire-and-forget pattern safely?

---

## Stretch exercise — `gather` with exceptions

This exercise has no starter file. Write it from scratch in a new file, e.g. `stretch_exceptions.py`.

### Scenario

You are probing a fleet of services; some are down and raise exceptions. You want to collect
results for the healthy ones while recording failures, rather than aborting the whole check.

### Spec

1. Write 5 coroutines named `probe_0` through `probe_4`. Three of them return a status string
   after a short `asyncio.sleep`; two raise `ConnectionError` with a descriptive message.

2. Call `asyncio.gather(*probes, return_exceptions=True)` and assign the result.

3. Iterate the result list and for each entry:
   - If it is an `Exception` instance, print `"FAIL: <exception message>"`.
   - Otherwise print `"OK: <result>"`.

4. Repeat the same gather call *without* `return_exceptions=True` and wrap it in a
   `try/except ConnectionError` block. Observe which result you get and which are silently lost.

### What to observe

- With `return_exceptions=True`: all 5 results are collected; you can distinguish successes
  from failures by type.
- Without `return_exceptions=True`: the first `ConnectionError` propagates immediately;
  the other coroutines may not have finished; you only see the one exception.

### Why this matters

Best-effort fan-out (collect everything, report failures inline) vs. fail-fast fan-out
(abort on first error) are a real architectural choice in microservice fan-outs, parallel
data pipelines, and concurrent API callers. `return_exceptions=True` is the best-effort switch.

---

## Backend tie-in — Fan-out / fan-in, latency vs. throughput

Two concepts that come up constantly in backend design:

**Fan-out / fan-in** is the pattern of sending one request to many downstream services in
parallel and then aggregating the responses. `gather` is the asyncio implementation of fan-in
— it waits for all the fanned-out tasks to complete.

**Latency vs. throughput** — concurrency hides latency; it does not increase throughput.
If each individual request takes 1 s and you run 10 of them concurrently, the wall-clock time
is ~1 s, not 10 s. But you are still doing 10 units of work — the *throughput* (requests per
second that the server must handle) has not changed. On a loaded server, running too many
concurrent requests can actually *increase* per-request latency due to resource contention.

One-liner for interviews: *"Concurrency hides latency by overlapping wait time; it does not
make individual operations faster and does not increase the server's capacity."*
