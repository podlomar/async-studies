"""
Section 2 — Tests for build_starter.py
=======================================

Run with:
    python -m unittest test_build.py -v

These tests verify the *observable behaviour* of your implementation:
- check_service prints start and finish lines and returns (name, status_code).
- check_all_serial runs checks sequentially (total time ≈ sum of delays).
- check_all_concurrent runs checks concurrently (total time ≈ max of delays).
- Both functions return the same results in the same order.

Network calls are stubbed so the tests run offline and deterministically.
The stub replaces requests.get with a fake that returns status 200 instantly;
the asyncio.sleep delays in check_service still fire so timing tests are valid.

The tests import your coroutines by name and signature:

    async def check_service(name: str, url: str, delay: float) -> tuple[str, int]
    async def check_all_serial(services: list[dict]) -> list[tuple[str, int]]
    async def check_all_concurrent(services: list[dict]) -> list[tuple[str, int]]
    async def main() -> None
"""

import asyncio
import importlib.util
import io
import pathlib
import re
import sys
import time
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Load the learner's module without executing the __main__ block.
# ---------------------------------------------------------------------------

def _load_starter() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_starter",
        pathlib.Path(__file__).parent / "build_starter.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _mod = _load_starter()
    check_service = _mod.check_service
    check_all_serial = _mod.check_all_serial
    check_all_concurrent = _mod.check_all_concurrent
    main = _mod.main
    _LOAD_ERROR = None
except Exception as exc:
    _LOAD_ERROR = exc


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _fake_response(status_code: int = 200) -> MagicMock:
    """Return a mock that looks enough like a requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def _stub_requests_get(mod: types.ModuleType):
    """
    Return a context manager that patches requests.get on the learner's
    module to return a 200 response immediately (no real network call).
    """
    return patch.object(mod.requests, "get", return_value=_fake_response(200))


# Minimal service list used in all tests — short delays keep the suite fast.
_TEST_SERVICES = [
    {"name": "alpha", "url": "https://example.com/a", "delay": 0.15},
    {"name": "beta",  "url": "https://example.com/b", "delay": 0.20},
    {"name": "gamma", "url": "https://example.com/c", "delay": 0.10},
]

_SERIAL_EXPECTED_MIN = sum(s["delay"] for s in _TEST_SERVICES) * 0.7
_CONCURRENT_EXPECTED_MAX = max(s["delay"] for s in _TEST_SERVICES) * 2.5


# ---------------------------------------------------------------------------
# Helper that captures stdout while running a coroutine.
# ---------------------------------------------------------------------------

class _CaptureRun:
    """Run a coroutine inside an IsolatedAsyncioTestCase; capture stdout."""

    @staticmethod
    async def run(coro):
        buf = io.StringIO()
        orig = sys.stdout
        sys.stdout = buf
        try:
            result = await coro
        finally:
            sys.stdout = orig
        lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
        return result, lines


# ---------------------------------------------------------------------------
# Tests for check_service
# ---------------------------------------------------------------------------

@unittest.skipIf(_LOAD_ERROR is not None, f"Could not import build_starter: {_LOAD_ERROR}")
class TestCheckService(unittest.IsolatedAsyncioTestCase):
    """check_service should print start/finish lines and return the right tuple."""

    async def _run(self, **kwargs):
        defaults = {"name": "test-svc", "url": "https://example.com", "delay": 0.05}
        defaults.update(kwargs)
        with _stub_requests_get(_mod):
            return await _CaptureRun.run(
                check_service(defaults["name"], defaults["url"], defaults["delay"])
            )

    async def test_returns_tuple(self):
        result, _ = await self._run()
        self.assertIsInstance(result, tuple, "check_service should return a tuple")

    async def test_returns_name_as_first_element(self):
        result, _ = await self._run(name="auth")
        self.assertEqual(result[0], "auth", "First element of tuple should be the service name")

    async def test_returns_status_code_as_second_element(self):
        result, _ = await self._run()
        self.assertEqual(
            result[1], 200,
            "Second element of tuple should be the HTTP status code (200 from stub)",
        )

    async def test_prints_two_lines(self):
        _, lines = await self._run()
        self.assertEqual(
            len(lines), 2,
            msg=f"Expected exactly 2 output lines (start + finish), got: {lines}",
        )

    async def test_first_line_contains_name(self):
        name = "payments"
        _, lines = await self._run(name=name)
        self.assertIn(name, lines[0], msg="First line should contain the service name")

    async def test_second_line_contains_name_and_elapsed(self):
        name = "payments"
        _, lines = await self._run(name=name)
        self.assertIn(name, lines[1], msg="Second line should contain the service name")
        self.assertRegex(
            lines[1],
            r"\d+\.\d+s",
            msg="Second line should contain elapsed time like '0.30s'",
        )

    async def test_respects_delay(self):
        t0 = time.perf_counter()
        with _stub_requests_get(_mod):
            await check_service("x", "https://example.com", delay=0.15)
        elapsed = time.perf_counter() - t0
        self.assertGreater(
            elapsed, 0.1,
            msg="check_service should await asyncio.sleep(delay); elapsed should be >= delay",
        )

    async def test_does_not_block_loop(self):
        """
        A heartbeat task must keep ticking while check_service is running.
        If check_service blocks the loop (e.g. calls requests.get directly),
        the heartbeat count will be 0.
        """
        ticks = []

        async def heartbeat():
            while True:
                ticks.append(time.perf_counter())
                await asyncio.sleep(0.02)

        hb_task = asyncio.create_task(heartbeat())
        with _stub_requests_get(_mod):
            await check_service("svc", "https://example.com", delay=0.15)
        hb_task.cancel()
        try:
            await hb_task
        except asyncio.CancelledError:
            pass

        self.assertGreater(
            len(ticks), 0,
            msg=(
                "The heartbeat task never ran while check_service was executing. "
                "This suggests check_service is blocking the event loop. "
                "Make sure you use asyncio.to_thread for the requests.get call."
            ),
        )


# ---------------------------------------------------------------------------
# Tests for check_all_serial
# ---------------------------------------------------------------------------

@unittest.skipIf(_LOAD_ERROR is not None, f"Could not import build_starter: {_LOAD_ERROR}")
class TestCheckAllSerial(unittest.IsolatedAsyncioTestCase):
    """check_all_serial should run services sequentially."""

    async def _run_serial(self):
        with _stub_requests_get(_mod):
            return await _CaptureRun.run(check_all_serial(_TEST_SERVICES))

    async def test_returns_list_of_correct_length(self):
        result, _ = await self._run_serial()
        self.assertEqual(
            len(result), len(_TEST_SERVICES),
            msg=f"check_all_serial should return one result per service, got {result}",
        )

    async def test_results_are_tuples(self):
        results, _ = await self._run_serial()
        for r in results:
            self.assertIsInstance(r, tuple, f"Each result should be a (name, status) tuple, got {r!r}")

    async def test_result_order_matches_input(self):
        results, _ = await self._run_serial()
        names = [r[0] for r in results]
        expected = [s["name"] for s in _TEST_SERVICES]
        self.assertEqual(names, expected, "Results should be in the same order as input services")

    async def test_prints_serial_total_line(self):
        _, lines = await self._run_serial()
        summary = [l for l in lines if "serial" in l.lower() and "total" in l.lower()]
        self.assertGreater(
            len(summary), 0,
            msg="check_all_serial should print a line containing 'serial' and 'total'",
        )

    async def test_serial_total_contains_elapsed_seconds(self):
        _, lines = await self._run_serial()
        summary = [l for l in lines if "serial" in l.lower() and "total" in l.lower()]
        self.assertTrue(
            any(re.search(r"\d+\.\d+s", l) for l in summary),
            msg="Serial total line should include elapsed time like '2.00s'",
        )

    async def test_serial_timing_is_approximately_sum_of_delays(self):
        """
        Sequential execution means total elapsed ≈ sum(delays).
        We allow a wide tolerance for slow environments but verify the time
        is NOT close to zero (which would mean delays were skipped).
        """
        t0 = time.perf_counter()
        with _stub_requests_get(_mod):
            await check_all_serial(_TEST_SERVICES)
        elapsed = time.perf_counter() - t0

        expected_sum = sum(s["delay"] for s in _TEST_SERVICES)
        self.assertGreater(
            elapsed, expected_sum * 0.6,
            msg=(
                f"Serial total ({elapsed:.2f}s) is much shorter than sum of delays "
                f"({expected_sum:.2f}s). Are the delays actually being awaited?"
            ),
        )

    async def test_serial_only_one_check_in_flight_at_a_time(self):
        """
        In serial mode the finish line for service N must appear before the
        start line for service N+1. We verify this by checking line ordering
        in the captured output.
        """
        _, lines = await self._run_serial()

        # Find start lines (contain service name but not an elapsed-time pattern).
        # Find finish/OK lines (contain elapsed time pattern).
        start_indices = [
            i for i, l in enumerate(lines)
            if any(s["name"] in l for s in _TEST_SERVICES)
            and not re.search(r"\d+\.\d+s", l)
            and "total" not in l.lower()
        ]
        finish_indices = [
            i for i, l in enumerate(lines)
            if re.search(r"\d+\.\d+s", l) and "total" not in l.lower()
        ]

        if len(start_indices) < 2 or len(finish_indices) < 2:
            # Can't verify ordering with fewer than 2 of each; skip assertion.
            return

        # finish of service i must come before start of service i+1.
        for i in range(len(finish_indices) - 1):
            if i < len(start_indices) - 1:
                self.assertLess(
                    finish_indices[i], start_indices[i + 1],
                    msg=(
                        f"In serial mode, finish of service {i} (output line {finish_indices[i]}) "
                        f"should appear before start of service {i+1} "
                        f"(output line {start_indices[i+1]}). "
                        "Are the checks running sequentially?"
                    ),
                )


# ---------------------------------------------------------------------------
# Tests for check_all_concurrent
# ---------------------------------------------------------------------------

@unittest.skipIf(_LOAD_ERROR is not None, f"Could not import build_starter: {_LOAD_ERROR}")
class TestCheckAllConcurrent(unittest.IsolatedAsyncioTestCase):
    """check_all_concurrent should run all services concurrently with gather."""

    async def _run_concurrent(self):
        with _stub_requests_get(_mod):
            return await _CaptureRun.run(check_all_concurrent(_TEST_SERVICES))

    async def test_returns_list_of_correct_length(self):
        result, _ = await self._run_concurrent()
        self.assertEqual(
            len(result), len(_TEST_SERVICES),
            msg=f"check_all_concurrent should return one result per service, got {result}",
        )

    async def test_results_are_tuples(self):
        results, _ = await self._run_concurrent()
        for r in results:
            self.assertIsInstance(r, tuple, f"Each result should be a (name, status) tuple, got {r!r}")

    async def test_result_order_matches_input(self):
        """
        gather preserves input order regardless of which coroutine finished first.
        """
        results, _ = await self._run_concurrent()
        names = [r[0] for r in results]
        expected = [s["name"] for s in _TEST_SERVICES]
        self.assertEqual(
            names, expected,
            "check_all_concurrent should return results in input order (gather preserves order)",
        )

    async def test_prints_concurrent_total_line(self):
        _, lines = await self._run_concurrent()
        summary = [l for l in lines if "concurrent" in l.lower() and "total" in l.lower()]
        self.assertGreater(
            len(summary), 0,
            msg="check_all_concurrent should print a line containing 'concurrent' and 'total'",
        )

    async def test_concurrent_total_contains_elapsed_seconds(self):
        _, lines = await self._run_concurrent()
        summary = [l for l in lines if "concurrent" in l.lower() and "total" in l.lower()]
        self.assertTrue(
            any(re.search(r"\d+\.\d+s", l) for l in summary),
            msg="Concurrent total line should include elapsed time like '0.20s'",
        )

    async def test_concurrent_timing_is_much_less_than_sum_of_delays(self):
        """
        Concurrent execution means total elapsed ≈ max(delays), not sum(delays).
        We verify that elapsed is well below the sum.
        """
        t0 = time.perf_counter()
        with _stub_requests_get(_mod):
            await check_all_concurrent(_TEST_SERVICES)
        elapsed = time.perf_counter() - t0

        expected_sum = sum(s["delay"] for s in _TEST_SERVICES)
        expected_max = max(s["delay"] for s in _TEST_SERVICES)

        self.assertGreater(
            elapsed, expected_max * 0.5,
            msg=(
                f"Concurrent total ({elapsed:.2f}s) seems impossibly fast — "
                "are the delays actually being awaited inside check_service?"
            ),
        )
        self.assertLess(
            elapsed, expected_sum * 0.8,
            msg=(
                f"Concurrent total ({elapsed:.2f}s) is close to the serial sum "
                f"({expected_sum:.2f}s). The checks do not appear to be running "
                "concurrently. Make sure you use asyncio.gather (not a serial for loop)."
            ),
        )

    async def test_concurrent_faster_than_serial(self):
        """The concurrent version must be meaningfully faster than serial."""
        with _stub_requests_get(_mod):
            t0 = time.perf_counter()
            await check_all_serial(_TEST_SERVICES)
            serial_elapsed = time.perf_counter() - t0

            t1 = time.perf_counter()
            await check_all_concurrent(_TEST_SERVICES)
            concurrent_elapsed = time.perf_counter() - t1

        self.assertLess(
            concurrent_elapsed, serial_elapsed * 0.75,
            msg=(
                f"Concurrent ({concurrent_elapsed:.2f}s) should be significantly faster "
                f"than serial ({serial_elapsed:.2f}s). "
                "Did you use asyncio.gather to schedule all coroutines at once?"
            ),
        )

    async def test_serial_and_concurrent_return_same_results(self):
        """Both functions must return identical result lists."""
        with _stub_requests_get(_mod):
            serial = await check_all_serial(_TEST_SERVICES)
            concurrent = await check_all_concurrent(_TEST_SERVICES)

        self.assertEqual(
            serial, concurrent,
            msg=(
                "check_all_serial and check_all_concurrent should return the same "
                f"results in the same order.\nSerial:     {serial}\nConcurrent: {concurrent}"
            ),
        )


# ---------------------------------------------------------------------------
# Tests for main()
# ---------------------------------------------------------------------------

@unittest.skipIf(_LOAD_ERROR is not None, f"Could not import build_starter: {_LOAD_ERROR}")
class TestMain(unittest.IsolatedAsyncioTestCase):
    """main() should run both modes and produce output."""

    async def _run_main(self):
        with _stub_requests_get(_mod):
            return await _CaptureRun.run(main())

    async def test_main_produces_output(self):
        _, lines = await self._run_main()
        self.assertGreater(len(lines), 0, msg="main() produced no output at all")

    async def test_main_output_mentions_serial(self):
        _, lines = await self._run_main()
        has_serial = any("serial" in l.lower() for l in lines)
        self.assertTrue(has_serial, msg="main() output should mention 'serial' (case-insensitive)")

    async def test_main_output_mentions_concurrent(self):
        _, lines = await self._run_main()
        has_concurrent = any("concurrent" in l.lower() for l in lines)
        self.assertTrue(
            has_concurrent, msg="main() output should mention 'concurrent' (case-insensitive)"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
