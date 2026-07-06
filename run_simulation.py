#!/usr/bin/env python3
"""
Master execution script for the Jhimpir Wind-UGES analysis suite.

Runs each analysis module in sequence and reports a pass/fail summary.
Each module is executed as a standalone process so it behaves exactly as it
does when run on its own, with no shared-state or import-path side effects.

Usage:
    python run_simulation.py            # run all modules
    python run_simulation.py --list     # list modules without running
"""
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Modules run in dependency-light order: resource/dispatch, then physical,
# then economic. Order does not affect results (each module is self-contained).
MODULES = [
    ("Grid load flow",             "loadflow/loadflow.py"),
    ("Energy-management dispatch", "ems/ems_dispatch.py"),
    ("Shaft settlement",           "settlement/settlement.py"),
    ("Structural verification",    "structural/structural.py"),
    ("Wire-rope factor of safety", "structural/rope_fos.py"),
    ("Strike survivability",       "resilience/resilience.py"),
    ("Life-cycle assessment",      "lca/lca.py"),
]


def run_module(label, relpath):
    script = ROOT / relpath
    if not script.exists():
        print(f"  [SKIP] {label}: file not found ({relpath})")
        return False
    print(f"\n{'=' * 64}\n  {label}  ({relpath})\n{'=' * 64}")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(script.parent),     # run from the module's own folder
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        print(f"  [FAIL] {label} (exit code {result.returncode})")
        if result.stderr:
            print("  stderr:")
            print("    " + result.stderr.rstrip().replace("\n", "\n    "))
        return False
    print(f"  [OK] {label}")
    return True


def main():
    if "--list" in sys.argv:
        print("Analysis modules:")
        for label, relpath in MODULES:
            print(f"  - {label}: {relpath}")
        return 0

    print("Jhimpir Wind-UGES analysis suite")
    print(f"Python {sys.version.split()[0]}  |  root: {ROOT}")

    results = [(label, run_module(label, relpath)) for label, relpath in MODULES]

    print(f"\n{'=' * 64}\n  SUMMARY\n{'=' * 64}")
    passed = sum(1 for _, ok in results if ok)
    for label, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n  {passed}/{len(results)} modules completed successfully.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
