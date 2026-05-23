# async-studies

A self-paced curriculum for learning Python `asyncio` from first principles to senior-level distributed systems. Each lesson explains the *why* before the *how*, with runnable practice exercises.

See [learning_roadmap.md](learning_roadmap.md) for the full plan with resources, project ideas, and competency milestones.

---

## Structure

```
phase-<N>/
  <NN>-<topic>/
    index.md       ← lesson with explanations and code examples
    practice/      ← runnable Python scripts
```

---

## Curriculum

### Phase 1 — Foundations of Concurrency

Understand what async replaces and why before touching any syntax.

| # | Topic | Status |
|---|-------|--------|
| 1.1 | [Synchronous Execution](phase-1/01-synchronous-execution/index.md) | done |
| 1.2 | [Processes vs Threads vs Async](phase-1/02-processes-threads-async/index.md) | done |

### Phase 2 — Asyncio Fundamentals

The core mental model: coroutines, the event loop, tasks, and futures.

| # | Topic | Status |
|---|-------|--------|
| 2.1 | [Coroutines and `async` / `await`](phase-2/01-coroutines-async-await/index.md) | done |
| 2.2 | [The Event Loop](phase-2/02-the-event-loop/index.md) | done |
| 2.3 | Tasks and Futures | — |

### Phase 3 — Intermediate Asyncio

Build real applications.

| # | Topic |
|---|-------|
| 3.1 | Async Networking (`aiohttp`, `httpx`) |
| 3.2 | Synchronization Primitives (locks, semaphores, queues) |
| 3.3 | Cancellation and Timeouts |
| 3.4 | Error Handling and `TaskGroup` |

### Phase 4 — Advanced Asyncio

Internals and production patterns.

| # | Topic |
|---|-------|
| 4.1 | Async Context Managers and Iterators |
| 4.2 | High-Performance Async Architecture |
| 4.3 | Asyncio Internals (epoll, transport/protocol, task state machines) |

### Phase 5 — Senior-Level Async Systems

Resilient distributed systems.

| # | Topic |
|---|-------|
| 5.1 | Production Async Services (observability, tracing) |
| 5.2 | Structured Concurrency |
| 5.3 | Async Database Systems |
| 5.4 | WebSockets and Realtime Systems |
| 5.5 | Distributed Async Architectures (queues, Kafka, Redis) |

### Phase 6 — Expert-Level Topics

| # | Topic |
|---|-------|
| 6.1 | Performance Engineering (profiling, event-loop lag) |
| 6.2 | Hybrid Concurrency (`run_in_executor`, `to_thread`) |
| 6.3 | Asyncio Design Patterns (circuit breakers, supervisors, bulkheads) |

---

## Prerequisites

- Python 3.11+
- `pip install aiohttp httpx asyncpg` for later phases
