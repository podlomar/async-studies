# 1.1 Synchronous Execution

> **Phase 1 — Foundations of Concurrency**
>
> Before learning `asyncio`, you need to understand what you're replacing and why.

---

## How Normal Python Execution Works

Python runs your code **line by line, top to bottom**. Each statement must complete before the next one starts. This is called *synchronous* or *sequential* execution.

```python
print("Step 1")
print("Step 2")
print("Step 3")
```

Output is always:
```
Step 1
Step 2
Step 3
```

There is no parallelism here. The interpreter advances only when the current instruction is done.

### The Main Thread

Every Python program starts with a single **main thread** — a single path of execution through the code. The operating system gives this thread CPU time to run. When it runs out of things to do (or deliberately waits), the OS can give that CPU time to another process.

By default, Python never gives that time away voluntarily. It holds the CPU until it's done with each instruction.

---

## Blocking Operations

A **blocking operation** is any call that makes your program wait before it can continue — the thread is stuck doing nothing useful while waiting for something external.

Common examples:

| Operation | What you're waiting for |
|---|---|
| `time.sleep(3)` | A timer in the OS |
| `requests.get(url)` | Network response |
| `file.read()` | Disk I/O |
| `input()` | The user to type |
| `subprocess.run(...)` | A child process to finish |

During a blocking call, your Python code is **frozen**. The CPU is idle (from your program's perspective), but your thread can't do anything else.

### Visualizing a Blocking HTTP Request

```
Timeline →

Thread: [---setup---][====WAITING FOR NETWORK====][---process response---]
CPU:    [   active  ][         idle              ][       active        ]
```

The `====` part is wasted time. The thread holds its place in the execution queue while doing nothing. This is the core inefficiency that `asyncio` solves.

---

## Call Stack Basics

The **call stack** tracks where Python is in your code at any given moment. Every time you call a function, a new *frame* is pushed onto the stack. When the function returns, its frame is popped off.

```python
def greet(name):       # frame 3 pushed, then popped
    return f"Hello, {name}"

def welcome(name):     # frame 2 pushed
    msg = greet(name)  # frame 3 pushed here
    print(msg)         # back to frame 2

def main():            # frame 1 pushed
    welcome("Alice")   # frame 2 pushed here

main()                 # execution starts
```

Stack state when `greet` is running:
```
[ greet("Alice")   ]  ← top (currently executing)
[ welcome("Alice") ]
[ main()           ]
[ <module>         ]  ← bottom
```

Python can only run one frame at a time. There is no concept of "meanwhile" in synchronous code. Every call waits for its callee to finish before proceeding.

### Why This Matters for Async

`asyncio` replaces this rigid one-at-a-time stack model with a *scheduler* that can suspend a coroutine mid-execution and resume it later. But that only works if functions explicitly yield control — which is what `await` does.

---

## CPU-Bound vs I/O-Bound Workloads

This distinction is the most important concept in all of concurrency. **The right tool depends entirely on which type of work you have.**

### CPU-Bound

A workload is **CPU-bound** when the bottleneck is computation. The processor is fully occupied doing calculations.

```python
import time

def find_primes(limit):
    primes = []
    for n in range(2, limit):
        if all(n % i != 0 for i in range(2, int(n**0.5) + 1)):
            primes.append(n)
    return primes

start = time.perf_counter()
result = find_primes(100_000)
elapsed = time.perf_counter() - start

print(f"Found {len(result)} primes in {elapsed:.3f}s")
```

The CPU never waits here. It's always computing. To speed this up you need **more CPU cores** — `asyncio` won't help, `multiprocessing` will.

### I/O-Bound

A workload is **I/O-bound** when the bottleneck is waiting for external resources: network, disk, database, user input.

```python
import time
import requests

def fetch_urls(urls):
    results = []
    for url in urls:
        response = requests.get(url)      # blocks here
        results.append(response.status_code)
    return results

urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]

start = time.perf_counter()
statuses = fetch_urls(urls)
elapsed = time.perf_counter() - start

print(f"Got {statuses} in {elapsed:.2f}s")  # ~3 seconds
```

The CPU is mostly idle here — it's waiting for the network. This is where `asyncio` shines. You can make all three requests *concurrently* and cut the time from ~3s to ~1s.

### The Decision Table

| Problem type | Bottleneck | Use |
|---|---|---|
| Image processing, ML training | CPU | `multiprocessing` |
| Web scraping, API calls | Network | `asyncio` / `aiohttp` |
| Reading thousands of files | Disk | `asyncio` or threads |
| Database queries at scale | Network + DB | `asyncio` + async driver |

---

## Key Concepts Summary

**Sequential execution** — instructions run one after another, in order. No statement starts until the previous one finishes.

**Latency** — the time between starting an operation and getting its result. A slow disk or distant server adds latency you can't compute away.

**Throughput** — how much work you complete per unit of time. Doing 10 things serially might take 10 seconds; doing them concurrently might take 1 second. Same work, far higher throughput.

**Waiting on I/O** — the thread is alive but idle, holding memory and a scheduler slot while doing nothing useful. This is the waste that concurrency models are designed to eliminate.

---

## Practice Exercises

### Exercise 1 — Measure a blocking read

Write a script that reads a large file line by line and counts the lines. Measure how long it takes using `time.perf_counter()`. Then measure how long the file open itself takes vs. the iteration.

```python
import time

def count_lines(path):
    start = time.perf_counter()
    with open(path, "r") as f:
        lines = f.readlines()
    elapsed = time.perf_counter() - start
    print(f"Read {len(lines)} lines in {elapsed:.4f}s")

# Generate a test file first:
with open("/tmp/test_data.txt", "w") as f:
    for i in range(500_000):
        f.write(f"Line number {i}\n")

count_lines("/tmp/test_data.txt")
```

**Goal:** Observe that even a simple file read has measurable latency.

---

### Exercise 2 — Sequential HTTP requests

Make 5 HTTP requests one after another and measure total time. Use `https://httpbin.org/delay/1` which deliberately waits 1 second before responding.

```python
import time
import requests

URLS = ["https://httpbin.org/delay/1"] * 5

def fetch_all_sequential(urls):
    results = []
    for i, url in enumerate(urls):
        start = time.perf_counter()
        r = requests.get(url)
        elapsed = time.perf_counter() - start
        print(f"  Request {i+1}: {r.status_code} in {elapsed:.2f}s")
        results.append(r.status_code)
    return results

print("Fetching sequentially...")
overall_start = time.perf_counter()
fetch_all_sequential(URLS)
overall_elapsed = time.perf_counter() - overall_start
print(f"Total: {overall_elapsed:.2f}s")
```

**Expected output:** ~5 seconds total. Each request waits for the previous.

**Goal:** Feel the pain of sequential I/O before you learn to fix it.

---

### Exercise 3 — Sleep between tasks

Simulate a system that does work, waits, and does more work. Measure each stage.

```python
import time

def process_batch(batch_id, items):
    print(f"  [Batch {batch_id}] Processing {len(items)} items...")
    time.sleep(0.5)  # simulate processing time
    print(f"  [Batch {batch_id}] Saving results...")
    time.sleep(0.3)  # simulate saving to disk
    print(f"  [Batch {batch_id}] Done.")

batches = [list(range(10 * i, 10 * i + 10)) for i in range(4)]

start = time.perf_counter()
for i, batch in enumerate(batches):
    process_batch(i, batch)
elapsed = time.perf_counter() - start

print(f"\nProcessed {len(batches)} batches in {elapsed:.2f}s")
```

**Expected output:** ~3.2 seconds total (4 batches × 0.8s each).

**Goal:** Recognize that each batch sits idle half the time waiting on I/O. This is exactly the gap that concurrency fills.

---

### Exercise 4 — Identify CPU-bound vs I/O-bound

Classify each of the following and explain *why*:

1. Resizing 1000 images with Pillow
2. Fetching the current price of 50 stocks from a REST API
3. Compressing a 2 GB file with gzip
4. Waiting for a database query across a network
5. Sorting a list of 10 million numbers
6. Tailing a log file and alerting on error patterns

Write your answers as comments in a Python file. Then time items 2 and 5 to test your intuition:

```python
import time
import requests

# --- I/O-bound: one API call ---
start = time.perf_counter()
r = requests.get("https://httpbin.org/get")
print(f"HTTP GET: {time.perf_counter() - start:.3f}s")

# --- CPU-bound: sorting ---
import random
data = random.sample(range(10_000_000), 10_000_000)
start = time.perf_counter()
data.sort()
print(f"Sort 10M items: {time.perf_counter() - start:.3f}s")
```

**Goal:** Build intuition for which category a problem falls into before reaching for a concurrency tool.

---

### Challenge — Profile your own blocking

Write a script that does three things sequentially:

1. Reads a file with 100,000 lines
2. Makes 3 HTTP requests to `https://httpbin.org/get`
3. Computes the sum of primes up to 50,000

Measure and print the time taken for each step separately and the total. Then answer:

- Which step was CPU-bound?
- Which steps were I/O-bound?
- Which step would benefit most from concurrency?

```python
import time
import requests

def time_it(label, fn):
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.3f}s")
    return result

# Step 1: file I/O
def read_file():
    with open("/tmp/test_data.txt") as f:
        return len(f.readlines())

# Step 2: network I/O
def fetch_three():
    return [requests.get("https://httpbin.org/get").status_code for _ in range(3)]

# Step 3: CPU work
def sum_primes():
    return sum(n for n in range(2, 50_000)
               if all(n % i != 0 for i in range(2, int(n**0.5) + 1)))

overall = time.perf_counter()
time_it("File read  ", read_file)
time_it("HTTP ×3    ", fetch_three)
time_it("Prime sum  ", sum_primes)
print(f"Total      : {time.perf_counter() - overall:.3f}s")
```

---

## What's Next

You now understand the cost of sequential execution. In **section 1.2** you'll see the three main ways Python addresses this cost — processes, threads, and async — and learn when to reach for each one.
