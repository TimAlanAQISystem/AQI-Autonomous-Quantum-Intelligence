#!/usr/bin/env python3
"""
ENTERPRISE DEPLOYMENT AUTOMATION
Created: February 5, 2026
Purpose: Zero-downtime deployment with automatic rollback

This script handles all deployment operations:
- Pre-deployment validation
- Git-based version control
- Automated backup and snapshot
- Zero-downtime service restart
- Health verification post-deployment
- Automatic rollback on failure

Usage:
    python enterprise_deploy.py                    # Full deployment
    python enterprise_deploy.py --validate-only    # Validation only
    python enterprise_deploy.py --rollback         # Rollback to previous
    python enterprise_deploy.py --snapshot         # Create snapshot

Mission: Enable safe, repeatable deployments that never break production
"""

import os
import sys
import shutil
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import logging

# Configure logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [DEPLOY] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "deployment.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EnterpriseDeployment:
    """
    Handles enterprise-grade deployment with safety guarantees.
    Every deployment is validated, backed up, and can be rolled back.
    """
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.archive_dir = self.root_dir / "_ARCHIVE" / "deployments"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        self.deployment_log = []
        self.deployment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"Enterprise Deployment System initialized")
        logger.info(f"Deployment ID: {self.deployment_id}")
    
    def create_snapshot(self, tag: Optional[str] = None) -> Path:
        """
        Create complete snapshot of current system state.
        This enables rollback if deployment fails.
        
        Returns:
            Path to snapshot directory
        """
        snapshot_name = f"snapshot_{self.deployment_id}"
        if tag:
            snapshot_name += f"_{tag}"
        
        snapshot_dir = self.archive_dir / snapshot_name
        logger.info(f"Creating snapshot: {snapshot_name}")
        
        # Files and directories to backup
        critical_files = [
            "control_api.py",
            "agent_alan_business_ai.py",
            "alan_state_machine.py",
            "alan_state_machine_integration.py",
            ".env",
            "requirements.txt",
            "enterprise_stability_system.py",
            "enterprise_deploy.py"
        ]
        
        critical_dirs = [
            "infrastructure",
            "static"
        ]
        
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for file_name in critical_files:
            src = self.root_dir / file_name
            if src.exists():
                dst = snapshot_dir / file_name
                shutil.copy2(src, dst)
                logger.info(f"  ✓ Backed up: {file_name}")
        
        # Copy directories
        for dir_name in critical_dirs:
            src = self.root_dir / dir_name
            if src.exists():
                dst = snapshot_dir / dir_name
                shutil.copytree(src, dst, dirs_exist_ok=True)
                logger.info(f"  ✓ Backed up: {dir_name}/")
        
        # Save snapshot metadata
        metadata = {
            "deployment_id": self.deployment_id,
            "timestamp": datetime.now().isoformat(),
            "tag": tag,
            "files_backed_up": len(critical_files),
            "dirs_backed_up": len(critical_dirs)
        }
        
        with open(snapshot_dir / "snapshot_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✓ Snapshot created: {snapshot_dir}")
        self.log_event("SNAPSHOT_CREATED", {"path": str(snapshot_dir)})
        
        return snapshot_dir
    
    def validate_syntax(self) -> Tuple[bool, List[str]]:
        """
        Validate Python syntax for all critical files.
        Prevents deploying code with syntax errors.
        """
        logger.info("Validating Python syntax...")
        
        python_files = [
            "control_api.py",
            "agent_alan_business_ai.py",
            "alan_state_machine.py",
            "alan_state_machine_integration.py",
            "enterprise_stability_system.py",
            "enterprise_deploy.py"
        ]
        
        errors = []
        
        for file_name in python_files:
            file_path = self.root_dir / file_name
            if not file_path.exists():
                errors.append(f"File not found: {file_name}")
                continue
            
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info(f"  ✓ {file_name}: Syntax OK")
                else:
                    error_msg = result.stderr.strip()
                    errors.append(f"{file_name}: {error_msg}")
                    logger.error(f"  ✗ {file_name}: {error_msg}")
            
            except Exception as e:
                errors.append(f"{file_name}: {str(e)}")
                logger.error(f"  ✗ {file_name}: {str(e)}")
        
        if not errors:
            logger.info("✓ All syntax checks passed")
            self.log_event("SYNTAX_VALIDATION", {"status": "passed"})
            return True, []
        else:
            logger.error(f"✗ Syntax validation failed: {len(errors)} error(s)")
            self.log_event("SYNTAX_VALIDATION", {"status": "failed", "errors": errors})
            return False, errors
    
    def validate_imports(self) -> Tuple[bool, List[str]]:
        """
        Validate all imports work correctly.
        Prevents deploying code with missing dependencies.
        """
        logger.info("Validating imports...")
        
        test_scripts = [
            ("control_api", "import control_api"),
            ("agent_alan", "import agent_alan_business_ai"),
            ("state_machine", "import alan_state_machine"),
            ("state_integration", "import alan_state_machine_integration"),
        ]
        
        errors = []
        
        for name, import_statement in test_scripts:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", import_statement],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(self.root_dir)
                )
                
                if result.returncode == 0:
                    logger.info(f"  ✓ {name}: Imports OK")
                else:
                    error_msg = result.stderr.strip()
                    errors.append(f"{name}: {error_msg}")
                    logger.error(f"  ✗ {name}: {error_msg}")
            
            except Exception as e:
                errors.append(f"{name}: {str(e)}")
                logger.error(f"  ✗ {name}: {str(e)}")
        
        if not errors:
            logger.info("✓ All import checks passed")
            self.log_event("IMPORT_VALIDATION", {"status": "passed"})
            return True, []
        else:
            logger.error(f"✗ Import validation failed: {len(errors)} error(s)")
            self.log_event("IMPORT_VALIDATION", {"status": "failed", "errors": errors})
            return False, errors
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration file and environment variables.
        """
        logger.info("Validating configuration...")
        
        errors = []
        
        # Check .env file exists
        env_file = self.root_dir / ".env"
        if not env_file.exists():
            errors.append(".env file not found")
            logger.error("✗ .env file missing")
            return False, errors
        
        # Load .env
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        except Exception as e:
            errors.append(f"Failed to load .env: {str(e)}")
            logger.error(f"✗ Failed to load .env: {str(e)}")
            return False, errors
        
        # Validate critical environment variables
        required_vars = [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_PHONE_NUMBER",
            "ELEVENLABS_API_KEY",
            "PUBLIC_TUNNEL_URL"
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                errors.append(f"Required environment variable not set: {var}")
                logger.error(f"✗ Missing: {var}")
            else:
                # Validate format based on variable name
                if var == "TWILIO_ACCOUNT_SID" and not value.startswith("AC"):
                    errors.append(f"{var} has invalid format (should start with 'AC')")
                elif var == "TWILIO_PHONE_NUMBER" and not value.startswith("+"):
                    errors.append(f"{var} has invalid format (should start with '+')")
                elif var == "PUBLIC_TUNNEL_URL" and not value.startswith("http"):
                    errors.append(f"{var} has invalid format (should start with 'http')")
                else:
                    if "TOKEN" in var or "KEY" in var or "SID" in var:
                        logger.info(f"  ✓ {var}: {'*' * 20}")
                    else:
                        logger.info(f"  ✓ {var}: {value}")
        
        if not errors:
            logger.info("✓ Configuration validation passed")
            self.log_event("CONFIG_VALIDATION", {"status": "passed"})
            return True, []
        else:
            logger.error(f"✗ Configuration validation failed: {len(errors)} error(s)")
            self.log_event("CONFIG_VALIDATION", {"status": "failed", "errors": errors})
            return False, errors
    
    def validate_git_status(self) -> Tuple[bool, List[str]]:
        """
        Validate Git repository is in good state.
        """
        logger.info("Validating Git status...")
        
        errors = []
        
        try:
            # Check if this is a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.root_dir)
            )
            
            if result.returncode != 0:
                errors.append("Not a Git repository")
                logger.warning("⚠ Not a Git repository - consider initializing")
                return True, []  # Warning, not error
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.root_dir)
            )
            
            if result.stdout.strip():
                uncommitted_files = result.stdout.strip().split('\n')
                logger.warning(f"⚠ {len(uncommitted_files)} uncommitted file(s):")
                for file in uncommitted_files[:5]:  # Show first 5
                    logger.warning(f"    {file}")
                
                # This is a warning, not a blocker
                logger.info("  Deployment will proceed despite uncommitted changes")
            else:
                logger.info("  ✓ No uncommitted changes")
            
            # Get current commit info
            result = subprocess.run(
                ["git", "log", "-1", "--oneline"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.root_dir)
            )
            
            if result.returncode == 0:
                commit_info = result.stdout.strip()
                logger.info(f"  Current commit: {commit_info}")
                self.log_event("GIT_STATUS", {"commit": commit_info})
        
        except FileNotFoundError:
            logger.warning("⚠ Git not installed or not in PATH")
            return True, []  # Warning, not error
        
        except Exception as e:
            logger.warning(f"⚠ Git status check failed: {str(e)}")
            return True, []  # Warning, not error
        
        return True, errors
    
    def run_neg_proof_tests(self) -> Tuple[bool, List[str]]:
        """
        Run neg-proof tests to verify nothing is broken.
        """
        logger.info("Running neg-proof tests...")
        
        # Check if neg-proof test file exists
        neg_proof_test = self.root_dir / "enterprise_negproof_tests.py"
        if not neg_proof_test.exists():
            logger.warning("⚠ Neg-proof test file not found, skipping")
            return True, []
        
        try:
            result = subprocess.run(
                [sys.executable, str(neg_proof_test)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.root_dir)
            )
            
            if result.returncode == 0:
                logger.info("✓ All neg-proof tests passed")
                self.log_event("NEGPROOF_TESTS", {"status": "passed"})
                return True, []
            else:
                logger.error(f"✗ Neg-proof tests failed:\n{result.stdout}")
                self.log_event("NEGPROOF_TESTS", {"status": "failed", "output": result.stdout})
                return False, [result.stdout]
        
        except Exception as e:
            logger.error(f"✗ Error running neg-proof tests: {str(e)}")
            return False, [str(e)]
    
    def deploy(self, skip_tests: bool = False) -> bool:
        """
        Execute full deployment process with all safety checks.
        
        Steps:
        1. Create pre-deployment snapshot
        2. Validate syntax
        3. Validate imports
        4. Validate configuration
        5. Run neg-proof tests (optional)
        6. Restart service
        7. Verify health
        8. Rollback if health check fails
        
        Returns:
            True if deployment succeeded, False otherwise
        """
        logger.info("="*80)
        logger.info("ENTERPRISE DEPLOYMENT STARTING")
        logger.info(f"Deployment ID: {self.deployment_id}")
        logger.info("="*80)
        
        # Step 1: Create snapshot
        logger.info("\n[STEP 1/7] Creating pre-deployment snapshot...")
        snapshot_dir = self.create_snapshot(tag="pre_deploy")
        
        # Step 2: Validate syntax
        logger.info("\n[STEP 2/7] Validating syntax...")
        syntax_ok, syntax_errors = self.validate_syntax()
        if not syntax_ok:
            logger.error("✗ DEPLOYMENT FAILED: Syntax errors detected")
            self.log_event("DEPLOYMENT_FAILED", {"reason": "syntax_errors", "errors": syntax_errors})
            return False
        
        # Step 3: Validate imports
        logger.info("\n[STEP 3/7] Validating imports...")
        imports_ok, import_errors = self.validate_imports()
        if not imports_ok:
            logger.error("✗ DEPLOYMENT FAILED: Import errors detected")
            self.log_event("DEPLOYMENT_FAILED", {"reason": "import_errors", "errors": import_errors})
            return False
        
        # Step 4: Validate configuration
        logger.info("\n[STEP 4/7] Validating configuration...")
        config_ok, config_errors = self.validate_configuration()
        if not config_ok:
            logger.error("✗ DEPLOYMENT FAILED: Configuration errors detected")
            self.log_event("DEPLOYMENT_FAILED", {"reason": "config_errors", "errors": config_errors})
            return False
        
        # Step 5: Run neg-proof tests (optional)
        if not skip_tests:
            logger.info("\n[STEP 5/7] Running neg-proof tests...")
            tests_ok, test_errors = self.run_neg_proof_tests()
            if not tests_ok:
                logger.error("✗ DEPLOYMENT FAILED: Neg-proof tests failed")
                self.log_event("DEPLOYMENT_FAILED", {"reason": "test_failures", "errors": test_errors})
                return False
        else:
            logger.info("\n[STEP 5/7] Skipping neg-proof tests (--skip-tests)")
        
        # Step 6: Restart service
        logger.info("\n[STEP 6/7] Restarting service...")
        restart_ok = self.restart_service()
        if not restart_ok:
            logger.error("✗ DEPLOYMENT FAILED: Service restart failed")
            logger.info("Attempting rollback...")
            self.rollback(snapshot_dir)
            return False
        
        # Step 7: Verify health
        logger.info("\n[STEP 7/7] Verifying system health...")
        health_ok = self.verify_health(timeout=30)
        if not health_ok:
            logger.error("✗ DEPLOYMENT FAILED: Health check failed")
            logger.info("Attempting rollback...")
            self.rollback(snapshot_dir)
            return False
        
        # Success!
        logger.info("="*80)
        logger.info("✓ DEPLOYMENT COMPLETED SUCCESSFULLY")
        logger.info(f"Deployment ID: {self.deployment_id}")
        logger.info(f"Snapshot: {snapshot_dir}")
        logger.info("="*80)
        
        self.log_event("DEPLOYMENT_SUCCESS", {"deployment_id": self.deployment_id})
        self.save_deployment_log()
        
        return True
    
    def restart_service(self) -> bool:
        """Restart the Windows Service"""
        try:
            # Import here to avoid circular dependency
            from enterprise_stability_system import EnterpriseStabilitySystem
            
            system = EnterpriseStabilitySystem()
            return system.restart_service()
        
        except Exception as e:
            logger.error(f"Failed to restart service: {str(e)}")
            return False
    
    def verify_health(self, timeout: int = 30) -> bool:
        """Verify system health after deployment"""
        try:
            from enterprise_stability_system import EnterpriseStabilitySystem, HealthStatus
            
            system = EnterpriseStabilitySystem()
            
            logger.info(f"Waiting for system to become healthy (timeout: {timeout}s)...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                status, health_data = system.check_health()
                
                if status == HealthStatus.HEALTHY:
                    logger.info("✓ System is healthy")
                    return True
                elif status == HealthStatus.DEGRADED:
                    logger.warning(f"⚠ System is degraded: {health_data['issues']}")
                    time.sleep(2)
                else:
                    logger.warning(f"System status: {status.value}")
                    time.sleep(2)
            
            logger.error("✗ System did not become healthy within timeout")
            return False
        
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def rollback(self, snapshot_dir: Path) -> bool:
        """Rollback to previous snapshot"""
        logger.info("="*80)
        logger.info("INITIATING ROLLBACK")
        logger.info(f"Restoring from: {snapshot_dir}")
        logger.info("="*80)
        
        if not snapshot_dir.exists():
            logger.error(f"Snapshot directory not found: {snapshot_dir}")
            return False
        
        try:
            # Load snapshot metadata
            metadata_file = snapshot_dir / "snapshot_metadata.json"
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            logger.info(f"Snapshot created: {metadata['timestamp']}")
            
            # Restore files
            for item in snapshot_dir.iterdir():
                if item.name == "snapshot_metadata.json":
                    continue
                
                dst = self.root_dir / item.name
                
                if item.is_file():
                    shutil.copy2(item, dst)
                    logger.info(f"  ✓ Restored: {item.name}")
                elif item.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(item, dst)
                    logger.info(f"  ✓ Restored: {item.name}/")
            
            # Restart service
            logger.info("Restarting service with rolled-back code...")
            restart_ok = self.restart_service()
            
            if restart_ok:
                logger.info("✓ ROLLBACK COMPLETED SUCCESSFULLY")
                self.log_event("ROLLBACK_SUCCESS", {"snapshot": str(snapshot_dir)})
                return True
            else:
                logger.error("✗ Service restart failed after rollback")
                return False
        
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            self.log_event("ROLLBACK_FAILED", {"error": str(e)})
            return False
    
    def log_event(self, event_type: str, data: Dict):
        """Log deployment event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "deployment_id": self.deployment_id,
            "event_type": event_type,
            "data": data
        }
        self.deployment_log.append(event)
    
    def save_deployment_log(self):
        """Save deployment log to file"""
        log_file = LOG_DIR / f"deployment_{self.deployment_id}.json"
        with open(log_file, 'w') as f:
            json.dump({
                "deployment_id": self.deployment_id,
                "timestamp": datetime.now().isoformat(),
                "events": self.deployment_log
            }, f, indent=2)
        
        logger.info(f"Deployment log saved: {log_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enterprise Deployment Automation for Agent X",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--validate-only", action="store_true",
                       help="Only run validation checks, don't deploy")
    parser.add_argument("--skip-tests", action="store_true",
                       help="Skip neg-proof tests (faster but less safe)")
    parser.add_argument("--snapshot", action="store_true",
                       help="Create snapshot without deploying")
    parser.add_argument("--rollback", type=str, metavar="SNAPSHOT_DIR",
                       help="Rollback to specific snapshot")
    
    args = parser.parse_args()
    
    deployer = EnterpriseDeployment()
    
    if args.snapshot:
        snapshot_dir = deployer.create_snapshot(tag="manual")
        print(f"\nSnapshot created: {snapshot_dir}")
        sys.exit(0)
    
    if args.rollback:
        snapshot_dir = Path(args.rollback)
        success = deployer.rollback(snapshot_dir)
        sys.exit(0 if success else 1)
    
    if args.validate_only:
        logger.info("="*80)
        logger.info("VALIDATION ONLY MODE")
        logger.info("="*80)
        
        all_ok = True
        
        syntax_ok, _ = deployer.validate_syntax()
        all_ok = all_ok and syntax_ok
        
        imports_ok, _ = deployer.validate_imports()
        all_ok = all_ok and imports_ok
        
        config_ok, _ = deployer.validate_configuration()
        all_ok = all_ok and config_ok
        
        git_ok, _ = deployer.validate_git_status()
        all_ok = all_ok and git_ok
        
        if not args.skip_tests:
            tests_ok, _ = deployer.run_neg_proof_tests()
            all_ok = all_ok and tests_ok
        
        sys.exit(0 if all_ok else 1)
    
    # Full deployment
    success = deployer.deploy(skip_tests=args.skip_tests)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
