# 3.1 Async Networking

> **Phase 3 — Intermediate Asyncio**
>
> Phase 2 gave you the mental model. Now apply it to the most common real-world use case: making many HTTP requests concurrently without blocking the event loop.

---

## Why Synchronous HTTP Fails at Scale

With `requests`, every call blocks the thread for the full round-trip:

```
GET /api/1  [====waiting 200ms====]
GET /api/2                          [====waiting 200ms====]
GET /api/3                                                  [====waiting 200ms====]
Total: 600ms
```

With an async client, the event loop fires all requests and waits only as long as the slowest one:

```
GET /api/1  [====waiting 200ms====]
GET /api/2  [====waiting 200ms====]
GET /api/3  [====waiting 200ms====]
Total: ~200ms
```

The difference scales linearly: 100 sequential requests at 200ms each = 20 seconds. 100 concurrent requests = ~200ms.

---

## The Two Main Libraries

### aiohttp

The most widely used async HTTP library. Has both a client and a server. Mature, battle-tested, extensive features.

```
pip install aiohttp
```

### httpx

A newer library with an API that closely mirrors `requests`. Supports both sync and async modes, HTTP/2, and has excellent timeout and retry ergonomics.

```
pip install httpx
```

Both are production-grade. `httpx` is easier to adopt if your team already knows `requests`; `aiohttp` is more common in older codebases and has more community examples. This section covers both.

---

## Basic GET Requests

### aiohttp

```python
import asyncio
import aiohttp

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    data = await fetch("https://httpbin.org/get")
    print(data["url"])

asyncio.run(main())
```

The double `async with` pattern appears constantly in aiohttp:
- The outer one manages the **session** (connection pool lifecycle)
- The inner one manages the **response** (reads the body, releases the connection)

### httpx

```python
import asyncio
import httpx

async def fetch(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

async def main():
    data = await fetch("https://httpbin.org/get")
    print(data["url"])

asyncio.run(main())
```

httpx reads the full response body automatically; no second `async with` needed for the response.

---

## Sessions and Connection Pooling

The most important rule in async HTTP: **create one session and reuse it**.

A session maintains a **connection pool** — a set of open TCP connections to each host. Reusing connections avoids the cost of a new TCP handshake and TLS negotiation for every request.

```python
# Bad — new TCP connection for every request
async def fetch_all_bad(urls):
    results = []
    for url in urls:
        async with aiohttp.ClientSession() as session:    # new pool each time
            async with session.get(url) as r:
                results.append(await r.json())
    return results

# Good — one pool shared across all requests
async def fetch_all_good(urls):
    async with aiohttp.ClientSession() as session:        # pool created once
        tasks = [fetch_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def fetch_one(session, url):
    async with session.get(url) as r:
        return await r.json()
```

### Why connection pooling matters

A TCP connection involves a handshake (~1 RTT) plus TLS negotiation (~1-2 RTTs). For 100 requests to the same host, that overhead dominates if you reconnect each time. A connection pool reuses established connections, reducing the overhead to near zero for subsequent requests.

aiohttp's default pool size is 100 connections per host. You can tune it:

```python
connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
async with aiohttp.ClientSession(connector=connector) as session:
    ...
```

httpx pools connections automatically within the `AsyncClient` lifetime.

---

## Timeouts

Never make an HTTP request without a timeout. A server that never responds will hang your coroutine indefinitely — and in production, eventually exhaust all your tasks.

### aiohttp timeouts

```python
import aiohttp
import asyncio

async def fetch_with_timeout(session, url):
    timeout = aiohttp.ClientTimeout(
        total=5.0,          # entire request: connect + read
        connect=2.0,        # time to establish connection
        sock_read=3.0,      # time to read response body
    )
    try:
        async with session.get(url, timeout=timeout) as r:
            return await r.json()
    except asyncio.TimeoutError:
        print(f"timed out: {url}")
        return None
```

### httpx timeouts

```python
import httpx

async def fetch_with_timeout(client, url):
    try:
        r = await client.get(url, timeout=httpx.Timeout(5.0, connect=2.0))
        return r.json()
    except httpx.TimeoutException:
        print(f"timed out: {url}")
        return None
```

### asyncio-level timeout (works with both)

You can also wrap any awaitable with `asyncio.timeout` (Python 3.11+):

```python
import asyncio

async def fetch_guarded(session, url):
    try:
        async with asyncio.timeout(5.0):
            async with session.get(url) as r:
                return await r.json()
    except TimeoutError:
        print(f"timed out: {url}")
        return None
```

Use the library-level timeout for fine-grained control (connect vs read separately). Use `asyncio.timeout` when you need a hard deadline across multiple operations.

---

## Retries

Transient network errors — connection resets, 503s, brief DNS failures — are normal in production. Retry logic makes your code resilient to them.

### Manual retry with exponential backoff

```python
import asyncio
import aiohttp

async def fetch_with_retry(session, url, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status == 200:
                    return await r.json()
                if r.status in (429, 503):       # rate limited or server overloaded
                    wait = 2 ** attempt           # 2s, 4s, 8s …
                    print(f"  {r.status} — retrying in {wait}s (attempt {attempt})")
                    await asyncio.sleep(wait)
                else:
                    r.raise_for_status()          # 4xx client errors — don't retry
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == max_attempts:
                raise
            wait = 2 ** attempt
            print(f"  error ({e}) — retrying in {wait}s (attempt {attempt})")
            await asyncio.sleep(wait)
    return None
```

### Key retry decisions

| Question | Guidance |
|---|---|
| Which errors to retry? | Network errors, 429, 503. Never 4xx client errors. |
| How long to wait? | Exponential backoff: 1s, 2s, 4s, 8s… |
| Add jitter? | Yes — `wait + random.uniform(0, 1)` prevents thundering herd |
| Max attempts? | 3–5 for user-facing paths; higher for background jobs |

---

## Rate Limiting with Semaphores

When hitting an API with rate limits (or when you want to be a good citizen and not flood a server), use a `Semaphore` to cap the number of in-flight requests.

```python
import asyncio
import aiohttp

async def fetch(session, sem, url):
    async with sem:                          # blocks when limit is reached
        async with session.get(url) as r:
            return r.status, url

async def main():
    urls = [f"https://httpbin.org/get?n={i}" for i in range(20)]
    sem = asyncio.Semaphore(5)              # max 5 concurrent requests

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, sem, url) for url in urls]
        results = await asyncio.gather(*tasks)

    for status, url in results:
        print(f"  {status}  {url}")

asyncio.run(main())
```

The semaphore does not slow down individual requests — it just ensures that at most 5 are in-flight simultaneously. Once one finishes, the next waiting coroutine acquires the semaphore and starts.

---

## Keep-Alive Connections

HTTP/1.1 connections are kept alive by default — the server holds the TCP socket open after responding, so the next request can reuse it without a new handshake. This is managed transparently by the session's connection pool.

You can observe keep-alive in action by watching connection counts:

```python
import asyncio
import aiohttp

async def main():
    connector = aiohttp.TCPConnector()
    async with aiohttp.ClientSession(connector=connector) as session:
        # First request — opens a connection
        async with session.get("https://httpbin.org/get") as r:
            await r.read()
        print(f"Connections after first: {len(connector._conns)}")

        # Second request — reuses the same connection
        async with session.get("https://httpbin.org/get") as r:
            await r.read()
        print(f"Connections after second: {len(connector._conns)}")

asyncio.run(main())
```

The same TCP connection handles both requests. This is why creating a new session for each request is so wasteful — you discard the connection before it can be reused.

---

## Backpressure

**Backpressure** is what happens when you produce work faster than the system can consume it. In HTTP terms: if you fire 10,000 concurrent requests, you will:

- Exhaust your OS's socket limit
- Overwhelm the server (triggering 429s or connection resets)
- Consume gigabytes of memory holding pending response buffers

The `Semaphore` pattern above is one form of backpressure control. A more structured approach uses a queue:

```python
import asyncio
import aiohttp

async def worker(session, queue, results):
    while True:
        url = await queue.get()
        try:
            async with session.get(url) as r:
                results.append((url, r.status))
        finally:
            queue.task_done()

async def main():
    urls = [f"https://httpbin.org/get?n={i}" for i in range(30)]
    results = []

    queue = asyncio.Queue()
    for url in urls:
        await queue.put(url)

    async with aiohttp.ClientSession() as session:
        workers = [
            asyncio.create_task(worker(session, queue, results))
            for _ in range(5)          # exactly 5 concurrent workers
        ]

        await queue.join()             # wait until all items are processed

        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    print(f"Fetched {len(results)} URLs")

asyncio.run(main())
```

The queue-based worker pool gives you natural backpressure: workers pull items only when they are free. New items pile up in the queue rather than creating new tasks unboundedly.

---

## Socket Lifecycle

Understanding what happens at the socket level helps you debug connection problems.

```
Client                          Server
  │                               │
  │── TCP SYN ───────────────────▶│
  │◀─ TCP SYN-ACK ────────────────│   handshake (~1 RTT)
  │── TCP ACK ───────────────────▶│
  │                               │
  │── TLS ClientHello ───────────▶│
  │◀─ TLS ServerHello + Cert ─────│   TLS (~1-2 RTTs)
  │── TLS Finished ──────────────▶│
  │                               │
  │── HTTP GET /path ────────────▶│   request
  │◀─ HTTP 200 OK + body ─────────│   response
  │                               │
  │  [connection kept alive]       │   keep-alive
  │                               │
  │── HTTP GET /other ───────────▶│   reused — no handshake
  │◀─ HTTP 200 OK + body ─────────│
```

When a connection pool is exhausted (all connections are busy), new requests queue up waiting for a slot. If `limit_per_host` is too low, you'll see requests taking far longer than the actual server response time — the extra time is spent waiting for a connection.

---

## Key Concepts Summary

**Session** — manages a connection pool. Create once, reuse everywhere. Never open a session per request.

**Connection pool** — a set of reusable TCP connections. Eliminates handshake overhead for repeated requests to the same host.

**Timeout** — set at connect, read, and total levels. Always set one; never leave requests unbounded.

**Retry** — retry on transient errors with exponential backoff and jitter. Never retry client errors (4xx).

**Semaphore** — caps concurrency. Use `asyncio.Semaphore(n)` to limit in-flight requests.

**Backpressure** — control the rate of work production. Use semaphores or worker queues to avoid overwhelming the server or your own system.

**Keep-alive** — HTTP/1.1 reuses TCP connections across requests. Managed automatically by the session.

---

## Practice Exercises

### Exercise 1 — Sequential vs concurrent HTTP

Compare sequential and concurrent fetching against a real slow endpoint.

```python
import asyncio
import aiohttp
import time

URLS = ["https://httpbin.org/delay/1"] * 5

async def fetch_one(session, url):
    async with session.get(url) as r:
        return r.status

async def sequential(session):
    return [await fetch_one(session, url) for url in URLS]

async def concurrent(session):
    return await asyncio.gather(*[fetch_one(session, url) for url in URLS])

async def main():
    async with aiohttp.ClientSession() as session:
        for label, fn in [("Sequential", sequential), ("Concurrent", concurrent)]:
            start = time.perf_counter()
            results = await fn(session)
            elapsed = time.perf_counter() - start
            print(f"{label}: {elapsed:.2f}s  statuses={results}")

asyncio.run(main())
```

**Expected:** Sequential ~5s, Concurrent ~1s.

---

### Exercise 2 — Timeout handling

Write a fetcher that gracefully handles both success and timeout.

```python
import asyncio
import aiohttp

URLS = [
    "https://httpbin.org/delay/0.5",    # fast
    "https://httpbin.org/delay/3",      # slow — will timeout
    "https://httpbin.org/get",          # instant
]

async def fetch(session, url, timeout_secs=1.0):
    timeout = aiohttp.ClientTimeout(total=timeout_secs)
    try:
        async with session.get(url, timeout=timeout) as r:
            return url, r.status, None
    except asyncio.TimeoutError:
        return url, None, "timeout"

async def main():
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch(session, url) for url in URLS])
    for url, status, error in results:
        if error:
            print(f"  FAIL  {url}  ({error})")
        else:
            print(f"  OK    {url}  {status}")

asyncio.run(main())
```

**Goal:** Handle timeouts without crashing the entire batch.

---

### Exercise 3 — Rate-limited API poller

Poll a paginated API endpoint concurrently, but at most 3 requests at a time.

```python
import asyncio
import aiohttp

async def fetch_page(session, sem, page):
    async with sem:
        url = f"https://httpbin.org/get?page={page}"
        async with session.get(url) as r:
            data = await r.json()
            return page, data["args"]["page"]

async def main():
    sem = asyncio.Semaphore(3)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_page(session, sem, p) for p in range(1, 11)]
        results = await asyncio.gather(*tasks)

    for page, val in sorted(results):
        print(f"  page {page}: received page={val}")

asyncio.run(main())
```

**Goal:** Understand how Semaphore controls concurrency without changing the gather structure.

---

### Exercise 4 — Web scraper

Scrape a list of URLs and extract status codes and content lengths.

```python
import asyncio
import aiohttp

URLS = [
    "https://httpbin.org/get",
    "https://httpbin.org/ip",
    "https://httpbin.org/user-agent",
    "https://httpbin.org/headers",
    "https://httpbin.org/uuid",
]

async def scrape(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            body = await r.read()
            return url, r.status, len(body)
    except Exception as e:
        return url, None, str(e)

async def main():
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[scrape(session, url) for url in URLS])

    print(f"{'URL':<45} {'STATUS':>6} {'BYTES':>8}")
    print("-" * 62)
    for url, status, size in results:
        print(f"{url:<45} {str(status):>6} {str(size):>8}")

asyncio.run(main())
```

**Goal:** Build a minimal concurrent scraper and inspect the results.

---

### Challenge — Resilient concurrent downloader

Build a downloader that fetches 10 URLs concurrently, retries transient failures, respects a semaphore limit, and reports a summary when done.

Requirements:
- Maximum 4 in-flight requests at a time
- Retry up to 3 times on network error or 5xx, with exponential backoff
- Report: total time, success count, failure count, URLs that failed

```python
import asyncio
import aiohttp
import time

URLS = [
    "https://httpbin.org/get?n=1",
    "https://httpbin.org/get?n=2",
    "https://httpbin.org/status/503",   # simulated server error
    "https://httpbin.org/get?n=4",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/get?n=6",
    "https://httpbin.org/status/500",   # simulated server error
    "https://httpbin.org/get?n=8",
    "https://httpbin.org/get?n=9",
    "https://httpbin.org/get?n=10",
]

async def fetch_with_retry(session, sem, url, max_attempts=3):
    # your implementation here
    ...

async def main():
    sem = asyncio.Semaphore(4)
    start = time.perf_counter()

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_retry(session, sem, url) for url in URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # report summary
    ...

asyncio.run(main())
```

**Stretch goal:** Use `as_completed` to print each result as it arrives instead of waiting for all.

---

## What's Next

You can now make robust concurrent HTTP requests with proper connection pooling, timeouts, retries, and backpressure control. In **section 3.2** you'll learn synchronization primitives — Locks, Semaphores, Queues, Events, and Conditions — for coordinating coroutines that share mutable state.
