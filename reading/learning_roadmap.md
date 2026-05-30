# Python `asyncio` Learning Roadmap

A progression from beginner fundamentals to senior-level concurrency architecture and production systems.

---

# Phase 1 — Foundations of Concurrency

Goal: Understand *why* asynchronous programming exists before learning syntax.

## 1. Synchronous Execution
Learn:
- How normal Python execution works
- Blocking operations
- Call stack basics
- CPU-bound vs I/O-bound workloads

Key concepts:
- Sequential execution
- Latency
- Throughput
- Waiting on I/O

Practice:
- Write scripts that:
  - Read files
  - Make HTTP requests
  - Sleep between tasks
- Measure runtime using `time.perf_counter()`

Recommended tools:
- Built-in `time`
- `requests`

---

## 2. Processes vs Threads vs Async
Learn:
- Multiprocessing
- Threading
- Cooperative multitasking
- GIL basics

Key concepts:
- Context switching
- Shared memory
- Race conditions
- Event-driven execution

You should understand:
| Model | Best For |
|---|---|
| Multiprocessing | CPU-heavy tasks |
| Threading | Blocking I/O with legacy code |
| asyncio | High-scale concurrent I/O |

Practice:
- Compare:
  - `threading`
  - `multiprocessing`
  - sequential execution

---

# Phase 2 — Asyncio Fundamentals

Goal: Learn the core mental model of `asyncio`.

## 1. Coroutines and `async` / `await`

Learn:
- What a coroutine is
- Difference between function and coroutine object
- `await`
- Suspension points

Core syntax:
```python
async def fetch():
    await asyncio.sleep(1)
```

Key concepts:
- Cooperative scheduling
- Non-blocking execution
- Awaitables

Practice:
- Build:
  - timer apps
  - concurrent sleeps
  - simple async workflows

Important milestone:
Understand why:
```python
asyncio.sleep()
```
is different from:
```python
time.sleep()
```

---

## 2. The Event Loop

Learn:
- What the event loop does
- Task scheduling
- Lifecycle of coroutines

Key APIs:
- `asyncio.run()`
- `get_running_loop()`
- loop policies

Key concepts:
- Ready queue
- Task switching
- Cooperative multitasking

Practice:
- Create multiple tasks
- Observe execution ordering

---

## 3. Tasks and Futures

Learn:
- `asyncio.create_task`
- Futures
- Awaiting multiple tasks

Key APIs:
- `create_task`
- `gather`
- `wait`
- `as_completed`

Practice:
- Parallel API requests
- Concurrent file downloads
- Fan-out/fan-in workflows

Critical concept:
Difference between:
```python
await coro()
```
and:
```python
asyncio.create_task(coro())
```

---

# Phase 3 — Intermediate Asyncio

Goal: Build real applications.

## 1. Async Networking

Learn:
- Async HTTP clients
- Connection pooling
- Timeouts
- Retries

Libraries:
- aiohttp
- httpx

Practice projects:
- Web scraper
- Concurrent API poller
- Rate-limited API client

Important concepts:
- Backpressure
- Socket lifecycle
- Keep-alive connections

---

## 2. Synchronization Primitives

Learn:
- Locks
- Semaphores
- Queues
- Events
- Conditions

Key APIs:
- `asyncio.Lock`
- `asyncio.Semaphore`
- `asyncio.Queue`

Practice:
- Worker pool
- Producer-consumer pipeline
- Rate limiter

Critical concept:
Even single-threaded async code can have race conditions.

---

## 3. Cancellation and Timeouts

Learn:
- Cooperative cancellation
- Timeout handling
- Graceful shutdown

Key APIs:
- `task.cancel()`
- `asyncio.timeout`
- `CancelledError`

Practice:
- Build cancellable jobs
- Graceful service shutdown

Senior-level insight:
Cancellation handling is one of the hardest parts of production async systems.

---

## 4. Error Handling

Learn:
- Exception propagation
- Partial failures
- Structured concurrency

Key APIs:
- `TaskGroup` (Python 3.11+)
- `return_exceptions=True`

Practice:
- Retry systems
- Failure-tolerant pipelines

You should understand:
- Why orphaned tasks are dangerous
- How unhandled exceptions leak resources

---

# Phase 4 — Advanced Asyncio

Goal: Understand internals and production patterns.

## 1. Async Context Managers and Iterators

Learn:
- `async with`
- `async for`

Practice:
- Streaming APIs
- Async DB cursors
- Resource lifecycle management

Libraries:
- asyncpg

---

## 2. High-Performance Async Architecture

Learn:
- Connection pools
- Batching
- Pipelines
- Backpressure strategies

Practice:
- Build:
  - async crawler
  - websocket server
  - event pipeline

Libraries:
- uvloop
- FastAPI

Topics:
- Memory pressure
- Queue sizing
- Throughput optimization

---

## 3. Asyncio Internals

Learn:
- Selector-based I/O
- Epoll/kqueue/IOCP
- Transport/protocol layer
- Task state machines

Topics:
- Scheduling fairness
- Starvation
- Callback queues

Read:
- CPython asyncio source code
- PEP 3156
- PEP 492

---

# Phase 5 — Senior-Level Async Systems

Goal: Design resilient distributed systems using async architecture.

## 1. Production Async Services

Learn:
- Observability
- Metrics
- Tracing
- Structured logging

Practice:
- Build:
  - async microservice
  - websocket gateway
  - event-driven backend

Tools:
- OpenTelemetry
- Prometheus

Critical concepts:
- Tail latency
- Cascading failures
- Load shedding

---

## 14. Structured Concurrency

Learn:
- Task lifetimes
- Cancellation trees
- Failure containment

Study:
- `TaskGroup`
- Trio-inspired patterns

Important idea:
Tasks should belong to a hierarchy and die together predictably.

---

## 15. Async Database Systems

Learn:
- Connection pooling
- Transaction management
- Streaming queries

Libraries:
- SQLAlchemy
- asyncpg

Practice:
- Async REST API
- Transaction retries
- High-concurrency workloads

Topics:
- Deadlocks
- Pool exhaustion
- Transaction isolation

---

## 16. WebSockets and Realtime Systems

Learn:
- Duplex communication
- Streaming
- Event broadcasting

Libraries:
- websockets

Practice:
- Chat server
- Live dashboard
- Multiplayer game backend

Senior concepts:
- Fan-out scaling
- Sticky sessions
- Flow control

---

## 17. Distributed Async Architectures

Learn:
- Message queues
- Event-driven systems
- Async workers

Technologies:
- Redis
- RabbitMQ
- Apache Kafka

Practice:
- Distributed job queue
- Event processing pipeline

Topics:
- Idempotency
- Exactly-once vs at-least-once delivery
- Eventual consistency

---

# Phase 6 — Expert-Level Topics

## 18. Performance Engineering

Learn:
- Profiling async applications
- Measuring event-loop lag
- Benchmarking concurrency

Tools:
- `py-spy`
- `scalene`
- asyncio debug mode

Metrics:
- Queue depth
- Task latency
- Throughput

---

## 19. Hybrid Concurrency

Learn:
- Combining:
  - asyncio
  - threads
  - multiprocessing

Key APIs:
- `run_in_executor`
- `to_thread`

Critical concept:
Never block the event loop with CPU-heavy work.

---

## 20. Asyncio Design Patterns

Master:
- Worker pools
- Pipelines
- Circuit breakers
- Retry orchestration
- Bulkheads
- Supervisors

Practice:
- Build production-grade resilient systems

---

# Recommended Project Progression

## Beginner
1. Concurrent sleep demo
2. Async downloader
3. API fetcher

## Intermediate
4. Web scraper
5. Async queue worker
6. Chat server

## Advanced
7. Rate-limited crawler
8. Streaming pipeline
9. Websocket gateway

## Senior
10. Distributed event processor
11. High-throughput API service
12. Real-time analytics platform

---

# Recommended Learning Resources

## Official Documentation
- https://docs.python.org/3/library/asyncio.html

## Books
- Python Concurrency with asyncio
- Fluent Python

## Frameworks Worth Studying
- FastAPI
- aiohttp
- AnyIO
- Trio

---

# Suggested Study Sequence

```text
Concurrency Basics
    ↓
async/await
    ↓
Tasks + Event Loop
    ↓
Networking
    ↓
Synchronization
    ↓
Cancellation + Error Handling
    ↓
Production Services
    ↓
Distributed Systems
    ↓
Performance Engineering
```

---

# Competency Milestones

## Beginner
You can:
- Write async functions
- Run concurrent tasks
- Use async HTTP clients

## Intermediate
You can:
- Build async services
- Handle cancellation correctly
- Coordinate concurrent workflows

## Advanced
You can:
- Design scalable async systems
- Diagnose performance bottlenecks
- Prevent event-loop starvation

## Senior
You can:
- Architect resilient distributed async systems
- Optimize high-throughput services
- Design concurrency models for production infrastructure
- Debug complex scheduling and cancellation failures
