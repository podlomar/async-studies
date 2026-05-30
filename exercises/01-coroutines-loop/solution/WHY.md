# Why things work the way they do — Section 1

## Core concept: coroutines are lazy; await is serial

Calling `async def f()` returns a **coroutine object**.  The function body has
not executed even one bytecode instruction.  Nothing happens until you either
`await` the coroutine or hand it to the event loop as a Task.

This is the sharpest contrast with JavaScript Promises: a Promise starts
executing its executor immediately when constructed.  A Python coroutine
object is inert until driven.

When you write:

```python
await download_small("small.csv")
await download_medium("medium.csv")
await download_large("large.csv")
```

The event loop runs `download_small` to completion, then `download_medium` to
completion, then `download_large` to completion.  At any instant only one of
them is active.  The total wall-clock time is therefore the sum of all delays,
just as if you had written three blocking `time.sleep` calls.

The key observation: `await` by itself does not create concurrency.  It means
"run this coroutine now and wait for it to finish."

## Why `asyncio.sleep` yields and `time.sleep` does not

`await asyncio.sleep(x)` works by scheduling a callback `x` seconds in the
future and then **returning control to the event loop**.  The loop is free to
run other coroutines (or do nothing if there are no others) until the timer
fires, at which point execution resumes after the `await`.

`time.sleep(x)` is a blocking system call.  It keeps the OS thread occupied
for `x` seconds.  The event loop does not get control back; nothing else in
the loop can run; the entire process is effectively frozen.

In Section 1 there are no other Tasks scheduled, so the distinction does not
matter yet — but in Section 2 and beyond it becomes critical.

## `asyncio.run` and the loop lifecycle

`asyncio.run(main())` does three things:

1. Creates a brand-new event loop.
2. Runs `main()` on that loop until `main` returns (or raises).
3. Cancels any remaining tasks, runs finalizers, and closes the loop.

It is the correct entry point in Python 3.12.  The older pattern of calling
`asyncio.get_event_loop().run_until_complete(main())` has deprecated
implicit-loop semantics and should not appear in new code.

Under the hood, `asyncio.run` is a thin wrapper around `asyncio.Runner`, the
lower-level context manager introduced in 3.11.  You rarely need `Runner`
directly, but knowing it exists helps when you see it in library source code.

## The diagnose bug explained

```python
result = fetch_status()     # no await
print(f"Health check response: {result}")
```

`fetch_status()` called without `await` returns a **coroutine object**, not
the string the function body would eventually produce.  The print therefore
outputs something like:

```
Health check response: <coroutine object fetch_status at 0x7f3a1b2c3d40>
```

When the program exits, Python's garbage collector destroys the coroutine
object.  Because the coroutine was never driven, Python emits:

```
RuntimeWarning: coroutine 'fetch_status' was never awaited
```

The cause is that CPython tracks whether a coroutine object has been
advanced at all.  If it reaches reference count zero without ever having been
sent a value, the warning fires.

The one-word fix is `await`:

```python
result = await fetch_status()
```

Now the event loop drives `fetch_status` to completion, the `return` value is
unwrapped from the coroutine, and `result` holds the string.

## The toy event loop (stretch)

A real event loop is, at its core, a priority queue of `(ready_at, callback)`
entries and a call to `select`/`epoll` to check for IO readiness.  Each
iteration:

1. Pop the earliest-due callback and call it.
2. If nothing is due yet, sleep until the soonest deadline.
3. Repeat until the queue is empty.

`await asyncio.sleep(x)` compiles down to: schedule the coroutine's
continuation as a callback at `now + x`, then yield to the loop.  When the
timer fires, the loop calls the callback, which resumes the coroutine.

Seeing this spelled out in ~20 lines of plain Python removes the mystery and
makes the rest of asyncio's behavior predictable.
