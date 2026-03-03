#!/usr/bin/env python3
"""
Run Complete Call Center Test Plan
Executes the comprehensive test suite for Agent X call center.
"""

import subprocess
import sys
import os

def run_test_plan():
    """Run the complete test plan."""
    print("Running Agent X Call Center Complete Test Plan...")

    try:
        # Run the test script
        result = subprocess.run([
            sys.executable,
            "test_call_center_complete.py"
        ], capture_output=True, text=True, cwd=os.getcwd())

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"\nExit Code: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"Error running test plan: {e}")
        return False

if __name__ == "__main__":
    success = run_test_plan()
    sys.exit(0 if success else 1)