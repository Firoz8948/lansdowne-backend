"""Minimal test runner used where pytest is not installed.

Tests that request pytest fixtures are skipped; run them with pytest.
"""

import inspect
import runpy
import sys
import traceback
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"


def main() -> int:
    selected = sys.argv[1:]
    paths = (
        [TESTS_DIR / name for name in selected]
        if selected
        else sorted(TESTS_DIR.glob("test_*.py"))
    )

    passed = 0
    skipped = 0
    failures: list[str] = []

    for path in paths:
        namespace = runpy.run_path(str(path))
        for name, value in sorted(namespace.items()):
            if not name.startswith("test_") or not callable(value):
                continue
            if inspect.signature(value).parameters:
                skipped += 1
                continue
            try:
                value()
            except Exception:
                failures.append(f"{path.name}::{name}\n{traceback.format_exc()}")
            else:
                passed += 1

    for failure in failures:
        print(failure)
    print(f"{passed} passed, {len(failures)} failed, {skipped} skipped (need pytest)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
