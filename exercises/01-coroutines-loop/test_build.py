"""
Section 1 — Tests for build_starter.py
=======================================

Run with:
    python -m unittest test_build.py -v

These tests verify the *observable behaviour* of your implementation:
- Each download coroutine prints its start and finish lines.
- Finish lines include the elapsed time in the expected format.
- main() runs all three downloads and prints a total-time summary line.
- Total elapsed time is approximately the sum of the individual delays
  (sequential execution, no concurrency).

The tests import your coroutines by name and drive them directly, so the
names and signatures in build_starter.py must match exactly:

    async def download_small(name: str) -> None
    async def download_medium(name: str) -> None
    async def download_large(name: str) -> None
    async def main() -> None
"""

import asyncio
import importlib
import io
import re
import sys
import time
import unittest


# ---------------------------------------------------------------------------
# Helper — import the learner's module without executing the __main__ block.
# ---------------------------------------------------------------------------

def _load_starter():
    """Import build_starter and return the module object."""
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "build_starter",
        pathlib.Path(__file__).parent / "build_starter.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _mod = _load_starter()
    download_small = _mod.download_small
    download_medium = _mod.download_medium
    download_large = _mod.download_large
    main = _mod.main
    _LOAD_ERROR = None
except Exception as exc:
    _LOAD_ERROR = exc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@unittest.skipIf(_LOAD_ERROR is not None, f"Could not import build_starter: {_LOAD_ERROR}")
class TestDownloadCoroutines(unittest.IsolatedAsyncioTestCase):
    """Each download coroutine should print its start and finish lines."""

    async def _capture(self, coro):
        """Run a coroutine and capture stdout; return (output_lines, elapsed)."""
        buf = io.StringIO()
        original = sys.stdout
        sys.stdout = buf
        t0 = time.perf_counter()
        try:
            await coro
        finally:
            sys.stdout = original
        elapsed = time.perf_counter() - t0
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        return lines, elapsed

    # --- download_small ---

    async def test_small_prints_two_lines(self):
        lines, _ = await self._capture(download_small("tiny.bin"))
        self.assertEqual(len(lines), 2, msg=f"Expected 2 lines, got: {lines}")

    async def test_small_start_line_contains_name(self):
        name = "tiny.bin"
        lines, _ = await self._capture(download_small(name))
        self.assertIn(name, lines[0], msg="First line should contain the file name")

    async def test_small_finish_line_contains_elapsed(self):
        lines, _ = await self._capture(download_small("tiny.bin"))
        # Finish line must contain a decimal number followed by 's'
        self.assertRegex(
            lines[1],
            r"\d+\.\d+s",
            msg="Finish line should contain elapsed time like '0.30s'",
        )

    async def test_small_takes_at_least_some_time(self):
        # The delay should be at least 0.1 s so it is a meaningful simulation.
        _, elapsed = await self._capture(download_small("tiny.bin"))
        self.assertGreater(elapsed, 0.1, msg="download_small should await asyncio.sleep for a noticeable duration")

    # --- download_medium ---

    async def test_medium_prints_two_lines(self):
        lines, _ = await self._capture(download_medium("data.csv"))
        self.assertEqual(len(lines), 2, msg=f"Expected 2 lines, got: {lines}")

    async def test_medium_takes_longer_than_small(self):
        _, small_elapsed = await self._capture(download_small("a"))
        _, medium_elapsed = await self._capture(download_medium("b"))
        self.assertGreater(
            medium_elapsed, small_elapsed,
            msg="download_medium should take longer than download_small",
        )

    # --- download_large ---

    async def test_large_prints_two_lines(self):
        lines, _ = await self._capture(download_large("archive.tar.gz"))
        self.assertEqual(len(lines), 2, msg=f"Expected 2 lines, got: {lines}")

    async def test_large_takes_longer_than_medium(self):
        _, medium_elapsed = await self._capture(download_medium("b"))
        _, large_elapsed = await self._capture(download_large("c"))
        self.assertGreater(
            large_elapsed, medium_elapsed,
            msg="download_large should take longer than download_medium",
        )


@unittest.skipIf(_LOAD_ERROR is not None, f"Could not import build_starter: {_LOAD_ERROR}")
class TestMainCoroutine(unittest.IsolatedAsyncioTestCase):
    """main() should run all three downloads and print a total-time summary."""

    async def _run_main(self):
        buf = io.StringIO()
        original = sys.stdout
        sys.stdout = buf
        t0 = time.perf_counter()
        try:
            await main()
        finally:
            sys.stdout = original
        elapsed = time.perf_counter() - t0
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        return lines, elapsed

    async def test_main_produces_output(self):
        lines, _ = await self._run_main()
        self.assertGreater(len(lines), 0, msg="main() produced no output")

    async def test_main_output_has_at_least_six_lines(self):
        # Three coroutines × 2 lines each = 6 lines minimum.
        lines, _ = await self._run_main()
        self.assertGreaterEqual(
            len(lines), 6,
            msg=(
                "Expected at least 6 output lines (start + finish for each of 3 downloads). "
                f"Got {len(lines)}: {lines}"
            ),
        )

    async def test_main_prints_total_time_line(self):
        lines, _ = await self._run_main()
        total_lines = [l for l in lines if "total" in l.lower()]
        self.assertGreater(
            len(total_lines), 0,
            msg="main() should print a line containing 'Total' (case-insensitive) with elapsed time",
        )

    async def test_total_line_contains_elapsed_seconds(self):
        lines, _ = await self._run_main()
        total_lines = [l for l in lines if "total" in l.lower()]
        self.assertTrue(
            any(re.search(r"\d+\.\d+s", l) for l in total_lines),
            msg="Total-time line should contain a value like '2.20s'",
        )

    async def test_sequential_execution_total_time(self):
        """
        Total time should be approximately the sum of individual delays.
        We allow ±30% tolerance for slow CI environments, but it must NOT be
        close to zero (which would mean the coroutines weren't actually awaited).
        """
        # Measure individual delays.
        async def _elapsed(coro):
            t = time.perf_counter()
            # Discard stdout.
            buf = io.StringIO()
            sys.stdout, orig = buf, sys.stdout
            try:
                await coro
            finally:
                sys.stdout = orig
            return time.perf_counter() - t

        t_small = await _elapsed(download_small("s"))
        t_medium = await _elapsed(download_medium("m"))
        t_large = await _elapsed(download_large("l"))
        expected_total = t_small + t_medium + t_large

        # Measure main() total.
        _, actual_total = await self._run_main()

        self.assertGreater(
            actual_total, expected_total * 0.7,
            msg=(
                "Total time is far shorter than the sum of delays — are the coroutines "
                "actually being awaited sequentially?"
            ),
        )
        self.assertLess(
            actual_total, expected_total * 1.5,
            msg=(
                "Total time is far longer than expected — something is taking much more "
                "time than the declared sleep durations."
            ),
        )

    async def test_all_three_names_appear_in_output(self):
        """Each download coroutine should print its name argument."""
        lines, _ = await self._run_main()
        # Count lines that look like a start line ("starting" keyword).
        start_lines = [l for l in lines if "start" in l.lower()]
        self.assertGreaterEqual(
            len(start_lines), 3,
            msg=(
                "Expected at least 3 'starting' lines (one per download). "
                f"Got {len(start_lines)}. Output: {lines}"
            ),
        )

    async def test_downloads_run_in_order(self):
        """
        small → medium → large must appear in that order in the output.
        We check that finish lines appear after their corresponding start lines
        and that no two downloads interleave (since they must be sequential).
        """
        lines, _ = await self._run_main()
        start_indices = [i for i, l in enumerate(lines) if "start" in l.lower()]
        # Finish lines contain a decimal-seconds value but are NOT the total-time summary.
        finish_indices = [
            i for i, l in enumerate(lines)
            if re.search(r"\d+\.\d+s", l) and "total" not in l.lower()
        ]

        self.assertEqual(
            len(start_indices), 3,
            msg=f"Expected 3 start lines, got {len(start_indices)}: {lines}",
        )
        self.assertEqual(
            len(finish_indices), 3,
            msg=f"Expected 3 finish lines (with elapsed time), got {len(finish_indices)}: {lines}",
        )

        # For each pair, the start index must precede the corresponding finish index.
        for i, (s, f) in enumerate(zip(start_indices, finish_indices)):
            self.assertLess(
                s, f,
                msg=f"Download #{i+1}: start line (index {s}) must appear before finish line (index {f})",
            )

        # Pairs must not interleave (sequential, not concurrent).
        # Finish of download N must come before start of download N+1.
        for i in range(len(finish_indices) - 1):
            self.assertLess(
                finish_indices[i], start_indices[i + 1],
                msg=(
                    f"Finish of download #{i+1} (index {finish_indices[i]}) should appear before "
                    f"start of download #{i+2} (index {start_indices[i+1]}). "
                    "Are the downloads sequential?"
                ),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
