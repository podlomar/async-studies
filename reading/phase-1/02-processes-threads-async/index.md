# 1.2 Processes vs Threads vs Async

> **Phase 1 — Foundations of Concurrency**
>
> You know that sequential execution wastes time waiting on I/O. Now meet the three tools Python gives you to reclaim that time — and understand which one to reach for when.

---

## The Core Problem, Restated

From section 1.1: a program making 5 network requests sequentially takes ~5 seconds. The CPU is idle for most of that time. Concurrency is about making use of that idle time.

Python offers three distinct models:

| Model | Mechanism | Best for |
|---|---|---|
| `multiprocessing` | Multiple OS processes | CPU-heavy work |
| `threading` | Multiple OS threads | Blocking I/O, legacy code |
| `asyncio` | Cooperative coroutines | High-scale concurrent I/O |

These are not interchangeable. Choosing the wrong one gets you either no speedup, or new bugs.

---

## Processes

A **process** is an isolated program instance. The OS gives it its own memory space, its own Python interpreter, and its own GIL (more on that shortly).

```
OS
├── Process A  (Python interpreter + memory)
│   └── Thread A1 (running your code)
├── Process B  (Python interpreter + memory)
│   └── Thread B1 (running your code)
└── Process C  ...
```

Because each process has its own interpreter, multiple processes can execute Python bytecode **truly simultaneously** on separate CPU cores. This is real parallelism.

### When to use processes

Use `multiprocessing` when your bottleneck is **CPU computation**: number crunching, image processing, ML inference, data transformation. The overhead of spawning a process (~100ms) and copying data between them is worth it only when the computation itself takes significant time.

```python
import multiprocessing
import time

def find_primes(limit):
    return sum(1 for n in range(2, limit)
               if all(n % i != 0 for i in range(2, int(n**0.5) + 1)))

if __name__ == "__main__":
    ranges = [50_000, 50_000, 50_000, 50_000]

    # Sequential
    start = time.perf_counter()
    results = [find_primes(r) for r in ranges]
    print(f"Sequential: {time.perf_counter() - start:.2f}s  → {results}")

    # Parallel processes
    start = time.perf_counter()
    with multiprocessing.Pool() as pool:
        results = pool.map(find_primes, ranges)
    print(f"Parallel:   {time.perf_counter() - start:.2f}s  → {results}")
```

On a 4-core machine this will be roughly 4x faster in the parallel version.

### The cost: no shared memory

Processes don't share memory. Passing data between them requires **serialisation** (pickling in Python). Sending a large object across a process boundary is expensive. This rules out processes for fine-grained coordination.

---

## Threads

A **thread** is a lighter unit of execution that lives *inside* a process. All threads in a process share the same memory space.

```
Process (one Python interpreter, one memory space)
├── Thread 1  (currently running)
├── Thread 2  (waiting for I/O)
└── Thread 3  (waiting for lock)
```

The OS **preemptively** switches between threads — it can pause Thread 1 mid-instruction and resume Thread 2. You don't control when switches happen.

### When to use threads

Threads are best for **blocking I/O** in situations where you can't use `asyncio` — for example, when using a library that has no async API (e.g. the standard `requests` library, most JDBC-style database drivers, `subprocess`).

```python
import threading
import time
import requests

results = {}

def fetch(url, index):
    r = requests.get(url)
    results[index] = r.status_code

urls = ["https://httpbin.org/delay/1"] * 5

# Sequential
start = time.perf_counter()
for i, url in enumerate(urls):
    fetch(url, i)
print(f"Sequential: {time.perf_counter() - start:.2f}s")  # ~5s

# Threaded
results.clear()
start = time.perf_counter()
threads = [threading.Thread(target=fetch, args=(url, i)) for i, url in enumerate(urls)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(f"Threaded:   {time.perf_counter() - start:.2f}s")  # ~1s
```

Threads cut the time to ~1 second because while one thread waits for the network, the OS runs another thread. The I/O happens concurrently even though the Python code is sequential.

### The cost: race conditions and the GIL

Shared memory is a double-edged sword. Two threads can read and write the same variable simultaneously, producing unpredictable results.

```python
import threading

counter = 0

def increment():
    global counter
    for _ in range(100_000):
        counter += 1  # not atomic — read, add, write are three steps

threads = [threading.Thread(target=increment) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()

print(counter)  # expected: 500_000 — actual: unpredictable
```

Run this several times. You'll get different values each time. This is a **race condition**: two threads interleave their read-modify-write steps and overwrite each other's work.

---

## The GIL

The **Global Interpreter Lock** (GIL) is a mutex inside CPython that allows only **one thread to execute Python bytecode at a time**.

```
Time →
Thread 1: [===run===][--wait--][===run===][--wait--]
Thread 2: [--wait--][===run===][--wait--][===run===]
              ↑ only one runs at a time
```

### What the GIL means in practice

- **For CPU-bound threads**: the GIL makes Python threads nearly useless for parallelism. Even on 8 cores, only one thread executes Python bytecode at a time. Threading cannot speed up CPU work.
- **For I/O-bound threads**: the GIL is released while a thread waits on I/O. Other threads can run while one is blocked. Threading *does* help with I/O.

This is why `multiprocessing` (each process has its own GIL) is needed for CPU work, and why `asyncio` (single-threaded, no GIL contention at all) is preferred for I/O.

> **Note (Python 3.13+):** The GIL can be disabled experimentally with `--disable-gil` / `PYTHON_GIL=0`. This may change the threading picture in future versions, but for now the GIL is still the default.

---

## Async / Cooperative Multitasking

`asyncio` takes a completely different approach. Instead of relying on the OS to switch between threads, it uses **cooperative multitasking**: code explicitly yields control when it's about to wait for something.

There is only one thread. A **scheduler** (the event loop) decides which coroutine runs next. A coroutine runs until it hits an `await`, then it's suspended and another coroutine gets the CPU.

```
Time →
Coroutine A: [==run==][........waiting........][==run==]
Coroutine B:         [==run==][....waiting....][==run==]
Coroutine C:                  [==run==][..wait..][==run==]
                  ↑ all interleaved, single thread
```

```python
import asyncio
import time

async def fetch_one(session, url, index):
    async with session.get(url) as r:
        print(f"  [{index}] status {r.status}")
        return r.status

async def main():
    import aiohttp
    urls = ["https://httpbin.org/delay/1"] * 5
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url, i) for i, url in enumerate(urls)]
        return await asyncio.gather(*tasks)

start = time.perf_counter()
asyncio.run(main())
print(f"Async: {time.perf_counter() - start:.2f}s")  # ~1s
```

All 5 requests are in flight simultaneously, from a single thread.

### Why async for I/O rather than threads?

| | Threads | Async |
|---|---|---|
| Switching | OS-controlled, preemptive | Explicit at `await` points |
| Race conditions | Yes — any line can be interrupted | Only at `await` points |
| Memory per unit | ~8 MB per thread stack | Kilobytes per coroutine |
| Max concurrency | Hundreds (OS limit) | Tens of thousands |
| Works with sync libs | Yes | No — needs async-native library |

For I/O-bound work at scale, async wins on all fronts except compatibility with legacy libraries.

---

## Context Switching

**Context switching** is the act of pausing one unit of execution and resuming another. It has a cost.

### OS-level context switch (processes/threads)

The OS must:
1. Save all CPU registers for the current thread
2. Update the OS scheduler tables
3. Restore CPU registers for the next thread

On modern hardware this takes roughly **1–10 microseconds**. At high concurrency (thousands of threads) this overhead becomes significant.

### Cooperative switch (async)

When `asyncio` switches from one coroutine to another, it just calls the next Python function on the event loop's queue. No OS involvement, no register save/restore at the kernel level. The cost is in the **nanosecond** range.

This is why async systems can handle tens of thousands of concurrent connections where thread-per-connection architectures struggle above a few hundred.

---

## Shared Memory

| Model | Memory sharing |
|---|---|
| Processes | No — each has its own address space |
| Threads | Yes — full access to all shared state |
| Async coroutines | Yes — same thread, same memory |

Threads and coroutines both share memory, but they differ in *when* they can be interrupted:

- A **thread** can be preempted between any two Python bytecode instructions — even inside `x += 1`.
- A **coroutine** can only be suspended at an explicit `await` — between `await` points, your code runs atomically from the perspective of other coroutines.

This makes async code easier to reason about than threaded code, even though both share memory.

---

## Race Conditions

A **race condition** occurs when the outcome of your program depends on the timing of concurrent operations. They produce bugs that are intermittent, hard to reproduce, and hard to test.

### Thread race condition

```python
# Shared state, no protection
balance = 1000

def withdraw(amount):
    global balance
    if balance >= amount:        # Thread A reads balance: 1000
                                 # Thread B reads balance: 1000 (same!)
        balance -= amount        # Thread A subtracts 800 → 200
                                 # Thread B subtracts 800 → 200 (wrong!)
```

Two threads both see `balance = 1000` and both proceed with the withdrawal. You end up with a negative balance.

### Async "race condition"

Async code is safer but not immune. A race can still happen across `await` boundaries:

```python
# Dangerous: state changes between awaits
async def transfer(from_account, to_account, amount):
    balance = await db.get_balance(from_account)
    if balance >= amount:
        # Another coroutine could modify the balance HERE
        await db.set_balance(from_account, balance - amount)
        await db.set_balance(to_account, amount)
```

Another coroutine can run between the `await` calls and change the database state. The fix is a database transaction — not a Python lock.

The key insight: **in async code, race conditions only occur at `await` points**. This makes them more predictable and easier to find than thread races.

---

## Event-Driven Execution

`asyncio`'s event loop is built on an **event-driven** model. Instead of threads sleeping and waking, the loop maintains a set of I/O handles and a queue of ready callbacks.

```
Event Loop iteration:
1. Check: which I/O handles are ready? (select/epoll/kqueue)
2. For each ready handle → schedule its callback
3. Run all scheduled callbacks until they yield (await)
4. Repeat
```

This is the same model used by Node.js, nginx, and most high-performance network servers. The OS's I/O multiplexing syscalls (`epoll` on Linux, `kqueue` on macOS) can monitor thousands of file descriptors simultaneously, notifying the event loop only when data is actually available.

The result: one thread can efficiently manage thousands of concurrent I/O operations without the memory or scheduling overhead of thousands of threads.

---

## Key Concepts Summary

**Context switching** — the cost of pausing one execution unit and resuming another. Cheap for coroutines (user-space), expensive for threads/processes (kernel-space).

**Shared memory** — threads and coroutines can read and write the same variables. Processes cannot without explicit IPC.

**Race conditions** — bugs caused by unsynchronised access to shared state. In threads they can happen anywhere; in async they only happen across `await` boundaries.

**Event-driven execution** — the event loop polls for I/O readiness and dispatches work only when something is ready, instead of having idle threads wait.

---

## Practice Exercises

### Exercise 1 — Three ways to fetch

Implement the same task three ways: fetch 5 URLs and collect their status codes. Compare the total runtime.

```python
import time
import threading
import requests

URLS = ["https://httpbin.org/delay/1"] * 5

# --- Sequential ---
def fetch_sequential(urls):
    return [requests.get(url).status_code for url in urls]

# --- Threaded ---
def fetch_threaded(urls):
    results = [None] * len(urls)

    def worker(i, url):
        results[i] = requests.get(url).status_code

    threads = [threading.Thread(target=worker, args=(i, url))
               for i, url in enumerate(urls)]
    for t in threads: t.start()
    for t in threads: t.join()
    return results

# --- Async (requires: pip install aiohttp) ---
import asyncio
import aiohttp

async def fetch_async(urls):
    async with aiohttp.ClientSession() as session:
        async def get(url):
            async with session.get(url) as r:
                return r.status
        return await asyncio.gather(*[get(url) for url in urls])

for label, fn in [
    ("Sequential", lambda: fetch_sequential(URLS)),
    ("Threaded  ", lambda: fetch_threaded(URLS)),
    ("Async     ", lambda: asyncio.run(fetch_async(URLS))),
]:
    start = time.perf_counter()
    result = fn()
    print(f"{label}: {time.perf_counter() - start:.2f}s  {result}")
```

**Expected:** Sequential ~5s, Threaded ~1s, Async ~1s.

**Goal:** See that both threading and async solve I/O concurrency, but async does it without spawning OS threads.

---

### Exercise 2 — CPU-bound: threads vs processes

Try to speed up a CPU-bound task with threads, then with processes. Observe that threads don't help.

```python
import time
import threading
import multiprocessing

def cpu_work(n):
    return sum(i * i for i in range(n))

N = 5_000_000
TASKS = [N] * 4

# Sequential
start = time.perf_counter()
results = [cpu_work(n) for n in TASKS]
print(f"Sequential:  {time.perf_counter() - start:.2f}s")

# Threaded (GIL prevents real parallelism)
results = [None] * 4
def worker(i, n):
    results[i] = cpu_work(n)

start = time.perf_counter()
threads = [threading.Thread(target=worker, args=(i, n)) for i, n in enumerate(TASKS)]
for t in threads: t.start()
for t in threads: t.join()
print(f"Threaded:    {time.perf_counter() - start:.2f}s  ← same as sequential!")

# Multiprocessing (real parallelism)
if __name__ == "__main__":
    start = time.perf_counter()
    with multiprocessing.Pool() as pool:
        results = pool.map(cpu_work, TASKS)
    print(f"Processes:   {time.perf_counter() - start:.2f}s  ← faster!")
```

**Goal:** Directly observe the GIL preventing thread-based speedup for CPU work.

---

### Exercise 3 — Trigger a race condition

Deliberately write a race condition with threads, observe inconsistent output, then fix it with a lock.

```python
import threading
import time

# Broken version
counter = 0

def increment_unsafe():
    global counter
    for _ in range(100_000):
        counter += 1

threads = [threading.Thread(target=increment_unsafe) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print(f"Unsafe:  expected 500000, got {counter}")  # likely wrong

# Fixed version
counter = 0
lock = threading.Lock()

def increment_safe():
    global counter
    for _ in range(100_000):
        with lock:
            counter += 1

threads = [threading.Thread(target=increment_safe) for _ in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print(f"Safe:    expected 500000, got {counter}")  # always correct
```

**Goal:** Make a race condition concrete, then understand why a lock fixes it.

---

### Exercise 4 — Count context switches

Use `time.perf_counter()` to measure the overhead of creating and joining many threads vs many coroutines.

```python
import time
import threading
import asyncio

N = 1000

# Thread overhead
def noop(): pass

start = time.perf_counter()
threads = [threading.Thread(target=noop) for _ in range(N)]
for t in threads: t.start()
for t in threads: t.join()
print(f"{N} threads:    {time.perf_counter() - start:.3f}s")

# Coroutine overhead
async def async_noop(): pass

async def run_coroutines():
    await asyncio.gather(*[async_noop() for _ in range(N)])

start = time.perf_counter()
asyncio.run(run_coroutines())
print(f"{N} coroutines: {time.perf_counter() - start:.3f}s")
```

**Expected:** Coroutines are noticeably faster to create and switch. At N=10_000 the difference becomes dramatic.

---

### Challenge — Which model would you choose?

For each scenario below, decide: `multiprocessing`, `threading`, or `asyncio`. Write your reasoning as a comment, then sketch out the implementation structure (you don't need to make real network calls).

```python
# Scenario A:
# You're building a CLI tool that resizes 500 photos.
# Answer: ?

# Scenario B:
# You're writing a web scraper that hits 200 URLs,
# using the requests library (no async version available).
# Answer: ?

# Scenario C:
# You're building a websocket server that holds
# 10,000 simultaneous live connections.
# Answer: ?

# Scenario D:
# You need to query 3 slow external REST APIs
# and combine their results. Each takes ~2 seconds.
# Answer: ?

# Scenario E:
# You're training a neural network using NumPy
# on a 16-core machine.
# Answer: ?
```

Answers: A→multiprocessing, B→threading, C→asyncio, D→threading or asyncio, E→multiprocessing (or a GPU library).

---

## What's Next

You now understand the three concurrency models and when each applies. Starting from **Phase 2**, you'll go deep on `asyncio` — beginning with coroutines and the `async`/`await` syntax that makes cooperative multitasking feel natural.
