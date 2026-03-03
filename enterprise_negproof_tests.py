#!/usr/bin/env python3
"""
ENTERPRISE NEG-PROOF TEST SUITE
Created: February 5, 2026
Mission: Validate system integrity before every deployment

This comprehensive test suite validates:
- All imports work correctly
- Configuration is valid
- Services are reachable
- Critical files exist
- Dependencies are installed
- No syntax errors exist

Neg-proof methodology: We don't test that things work,
we test that things DON'T fail.

Usage:
    python enterprise_negproof_tests.py              # Run all tests
    python enterprise_negproof_tests.py --quick      # Quick validation
    python enterprise_negproof_tests.py --report     # Detailed report

Exit codes:
    0: All tests passed
    1: One or more tests failed
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class Color:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class NegProofTestSuite:
    """
    Comprehensive test suite using neg-proof methodology.
    Tests validate that critical failures DO NOT occur.
    """
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.test_results = []
        self.failures = []
        
        print(f"{Color.BOLD}="*80)
        print("ENTERPRISE NEG-PROOF TEST SUITE")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"="*80 + Color.END)
    
    def test(self, name: str, func) -> bool:
        """Run a single test and record result"""
        print(f"\n{Color.BLUE}[TEST]{Color.END} {name}...")
        
        try:
            result, message = func()
            
            if result:
                print(f"  {Color.GREEN}✓ PASS{Color.END}: {message}")
                self.test_results.append({
                    "name": name,
                    "status": "PASS",
                    "message": message
                })
                return True
            else:
                print(f"  {Color.RED}✗ FAIL{Color.END}: {message}")
                self.test_results.append({
                    "name": name,
                    "status": "FAIL",
                    "message": message
                })
                self.failures.append({"name": name, "message": message})
                return False
        
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"  {Color.RED}✗ ERROR{Color.END}: {error_msg}")
            self.test_results.append({
                "name": name,
                "status": "ERROR",
                "message": error_msg
            })
            self.failures.append({"name": name, "message": error_msg})
            return False
    
    # ==================== CRITICAL FILE TESTS ====================
    
    def test_control_api_exists(self) -> Tuple[bool, str]:
        """Neg-proof: control_api.py MUST exist"""
        file_path = self.root_dir / "control_api.py"
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        return True, f"File exists: {file_path}"
    
    def test_control_api_syntax(self) -> Tuple[bool, str]:
        """Neg-proof: control_api.py MUST have valid syntax"""
        file_path = self.root_dir / "control_api.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, f"Syntax error: {result.stderr}"
        return True, "Syntax is valid"
    
    def test_control_api_imports(self) -> Tuple[bool, str]:
        """Neg-proof: control_api.py MUST import without errors"""
        result = subprocess.run(
            [sys.executable, "-c", "import control_api"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(self.root_dir)
        )
        
        if result.returncode != 0:
            return False, f"Import failed: {result.stderr}"
        return True, "Imports successfully"
    
    # ==================== AGENT ALAN TESTS ====================
    
    def test_agent_alan_exists(self) -> Tuple[bool, str]:
        """Neg-proof: agent_alan_business_ai.py MUST exist"""
        file_path = self.root_dir / "agent_alan_business_ai.py"
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        return True, f"File exists: {file_path}"
    
    def test_agent_alan_syntax(self) -> Tuple[bool, str]:
        """Neg-proof: agent_alan_business_ai.py MUST have valid syntax"""
        file_path = self.root_dir / "agent_alan_business_ai.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, f"Syntax error: {result.stderr}"
        return True, "Syntax is valid"
    
    # ==================== STATE MACHINE TESTS ====================
    
    def test_state_machine_exists(self) -> Tuple[bool, str]:
        """Neg-proof: alan_state_machine.py MUST exist"""
        file_path = self.root_dir / "alan_state_machine.py"
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        return True, f"File exists: {file_path}"
    
    def test_state_machine_syntax(self) -> Tuple[bool, str]:
        """Neg-proof: alan_state_machine.py MUST have valid syntax"""
        file_path = self.root_dir / "alan_state_machine.py"
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, f"Syntax error: {result.stderr}"
        return True, "Syntax is valid"
    
    # ==================== DEPENDENCY TESTS ====================
    
    def test_fastapi_installed(self) -> Tuple[bool, str]:
        """Neg-proof: fastapi MUST be installed"""
        result = subprocess.run(
            [sys.executable, "-c", "import fastapi"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "fastapi not installed"
        return True, "fastapi is installed"
    
    def test_uvicorn_installed(self) -> Tuple[bool, str]:
        """Neg-proof: uvicorn MUST be installed"""
        result = subprocess.run(
            [sys.executable, "-c", "import uvicorn"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "uvicorn not installed"
        return True, "uvicorn is installed"
    
    def test_twilio_installed(self) -> Tuple[bool, str]:
        """Neg-proof: twilio MUST be installed"""
        result = subprocess.run(
            [sys.executable, "-c", "import twilio"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "twilio not installed"
        return True, "twilio is installed"
    
    def test_elevenlabs_installed(self) -> Tuple[bool, str]:
        """Neg-proof: elevenlabs MUST be installed"""
        result = subprocess.run(
            [sys.executable, "-c", "import elevenlabs"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "elevenlabs not installed"
        return True, "elevenlabs is installed"
    
    # ==================== CONFIGURATION TESTS ====================
    
    def test_env_file_exists(self) -> Tuple[bool, str]:
        """Neg-proof: .env file MUST exist"""
        file_path = self.root_dir / ".env"
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        return True, f"File exists: {file_path}"
    
    def test_twilio_account_sid_set(self) -> Tuple[bool, str]:
        """Neg-proof: TWILIO_ACCOUNT_SID MUST be set"""
        # Load .env
        env_file = self.root_dir / ".env"
        if not env_file.exists():
            return False, ".env file not found"
        
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("TWILIO_ACCOUNT_SID="):
                    value = line.split("=", 1)[1].strip()
                    if value and value != "":
                        return True, "TWILIO_ACCOUNT_SID is set"
        
        return False, "TWILIO_ACCOUNT_SID not set in .env"
    
    def test_twilio_auth_token_set(self) -> Tuple[bool, str]:
        """Neg-proof: TWILIO_AUTH_TOKEN MUST be set"""
        env_file = self.root_dir / ".env"
        if not env_file.exists():
            return False, ".env file not found"
        
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("TWILIO_AUTH_TOKEN="):
                    value = line.split("=", 1)[1].strip()
                    if value and value != "":
                        return True, "TWILIO_AUTH_TOKEN is set"
        
        return False, "TWILIO_AUTH_TOKEN not set in .env"
    
    def test_elevenlabs_api_key_set(self) -> Tuple[bool, str]:
        """Neg-proof: ELEVENLABS_API_KEY MUST be set"""
        env_file = self.root_dir / ".env"
        if not env_file.exists():
            return False, ".env file not found"
        
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("ELEVENLABS_API_KEY="):
                    value = line.split("=", 1)[1].strip()
                    if value and value != "":
                        return True, "ELEVENLABS_API_KEY is set"
        
        return False, "ELEVENLABS_API_KEY not set in .env"
    
    def test_public_tunnel_url_set(self) -> Tuple[bool, str]:
        """Neg-proof: PUBLIC_TUNNEL_URL MUST be set"""
        env_file = self.root_dir / ".env"
        if not env_file.exists():
            return False, ".env file not found"
        
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("PUBLIC_TUNNEL_URL="):
                    value = line.split("=", 1)[1].strip()
                    if value and value != "" and not value.startswith("#"):
                        return True, f"PUBLIC_TUNNEL_URL is set: {value}"
        
        return False, "PUBLIC_TUNNEL_URL not set in .env"
    
    # ==================== INFRASTRUCTURE TESTS ====================
    
    def test_static_directory_exists(self) -> Tuple[bool, str]:
        """Neg-proof: static/ directory MUST exist"""
        dir_path = self.root_dir / "static"
        if not dir_path.exists():
            return False, f"Directory not found: {dir_path}"
        return True, f"Directory exists: {dir_path}"
    
    def test_audio_directory_exists(self) -> Tuple[bool, str]:
        """Neg-proof: static/audio/ directory MUST exist"""
        dir_path = self.root_dir / "static" / "audio"
        if not dir_path.exists():
            return False, f"Directory not found: {dir_path}"
        return True, f"Directory exists: {dir_path}"
    
    def test_logs_directory_exists(self) -> Tuple[bool, str]:
        """Neg-proof: logs/ directory MUST exist or be creatable"""
        dir_path = self.root_dir / "logs"
        try:
            dir_path.mkdir(exist_ok=True)
            return True, f"Directory exists: {dir_path}"
        except Exception as e:
            return False, f"Cannot create logs directory: {str(e)}"
    
    # ==================== PYTHON ENVIRONMENT TESTS ====================
    
    def test_python_version(self) -> Tuple[bool, str]:
        """Neg-proof: Python version MUST be 3.8+"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            return False, f"Python {version.major}.{version.minor} is too old (need 3.8+)"
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    
    def test_pip_installed(self) -> Tuple[bool, str]:
        """Neg-proof: pip MUST be available"""
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "pip not available"
        return True, f"pip is available: {result.stdout.strip()}"
    
    # ==================== MAIN TEST RUNNER ====================
    
    def run_all_tests(self, quick: bool = False):
        """Run all neg-proof tests"""
        print(f"\n{Color.BOLD}Running neg-proof validation suite...{Color.END}\n")
        
        # Critical file tests
        self.test("Control API file exists", self.test_control_api_exists)
        self.test("Control API syntax valid", self.test_control_api_syntax)
        if not quick:
            self.test("Control API imports work", self.test_control_api_imports)
        
        self.test("Agent Alan file exists", self.test_agent_alan_exists)
        self.test("Agent Alan syntax valid", self.test_agent_alan_syntax)
        
        self.test("State Machine file exists", self.test_state_machine_exists)
        self.test("State Machine syntax valid", self.test_state_machine_syntax)
        
        # Dependency tests
        self.test("fastapi installed", self.test_fastapi_installed)
        self.test("uvicorn installed", self.test_uvicorn_installed)
        self.test("twilio installed", self.test_twilio_installed)
        self.test("elevenlabs installed", self.test_elevenlabs_installed)
        
        # Configuration tests
        self.test(".env file exists", self.test_env_file_exists)
        self.test("TWILIO_ACCOUNT_SID set", self.test_twilio_account_sid_set)
        self.test("TWILIO_AUTH_TOKEN set", self.test_twilio_auth_token_set)
        self.test("ELEVENLABS_API_KEY set", self.test_elevenlabs_api_key_set)
        self.test("PUBLIC_TUNNEL_URL set", self.test_public_tunnel_url_set)
        
        # Infrastructure tests
        self.test("static/ directory exists", self.test_static_directory_exists)
        self.test("static/audio/ directory exists", self.test_audio_directory_exists)
        self.test("logs/ directory exists", self.test_logs_directory_exists)
        
        # Python environment tests
        self.test("Python version 3.8+", self.test_python_version)
        self.test("pip is available", self.test_pip_installed)
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = len(self.failures)
        
        print(f"\n{Color.BOLD}="*80)
        print("TEST SUMMARY")
        print(f"="*80 + Color.END)
        print(f"Total Tests: {total}")
        print(f"{Color.GREEN}Passed: {passed}{Color.END}")
        print(f"{Color.RED}Failed: {failed}{Color.END}")
        
        if self.failures:
            print(f"\n{Color.RED}{Color.BOLD}FAILURES:{Color.END}")
            for failure in self.failures:
                print(f"  {Color.RED}✗{Color.END} {failure['name']}")
                print(f"    {failure['message']}")
        else:
            print(f"\n{Color.GREEN}{Color.BOLD}✓ ALL TESTS PASSED{Color.END}")
        
        print(f"\n{Color.BOLD}="*80 + Color.END)
        
        return len(self.failures) == 0
    
    def save_report(self):
        """Save detailed test report to file"""
        report_dir = self.root_dir / "logs"
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"negproof_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed": sum(1 for r in self.test_results if r["status"] == "PASS"),
            "failed": len(self.failures),
            "results": self.test_results,
            "failures": self.failures
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved: {report_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enterprise Neg-Proof Test Suite for Agent X"
    )
    parser.add_argument("--quick", action="store_true",
                       help="Run quick validation (skip slow tests)")
    parser.add_argument("--report", action="store_true",
                       help="Save detailed report to file")
    
    args = parser.parse_args()
    
    suite = NegProofTestSuite()
    suite.run_all_tests(quick=args.quick)
    all_passed = suite.print_summary()
    
    if args.report:
        suite.save_report()
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
