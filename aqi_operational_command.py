#!/usr/bin/env python3
"""
AQI Operational Command Interface
Accepts founder-grade operational orders and executes them through the autonomous media pipeline
"""

import sys
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from aqi_media_pipeline import AQIMediaPipeline

def main():
    """Main entry point for AQI operational commands"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("🔥 AQI Operational Command Interface")
        print("Usage: python aqi_operational_command.py \"AQI, execute the Full Documentary Completion Protocol...\"")
        print()
        print("Example operational order:")
        print("\"AQI, execute the Full Documentary Completion Protocol. Render all chapters, verify all outputs, assemble the final 20-minute video, and complete the project with every module connected and zero delays. Begin immediately and continue until the documentary is fully completed and verified.\"")
        sys.exit(1)

    # Combine all arguments into the command
    command = " ".join(sys.argv[1:])

    print("🔥 AQI Operational Command Interface Activated")
    print(f"Command received: {command}")
    print()

    try:
        # Initialize the autonomous media pipeline
        print("🚀 Initializing AQI Autonomous Media Pipeline...")
        pipeline = AQIMediaPipeline()

        # Execute the operational order
        print("🎯 Executing operational order...")
        success = pipeline.execute_operational_order(command)

        if success:
            print()
            print("🎉 OPERATIONAL ORDER EXECUTED SUCCESSFULLY")
            print("The AQI documentary production has been initiated.")
            print("All modules are connected and operating with zero delays.")
            print()
            print("Status:", pipeline.get_status())
        else:
            print()
            print("❌ OPERATIONAL ORDER EXECUTION FAILED")
            print("Check logs for details.")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Critical error during command execution: {e}")
        logging.exception("Command execution failed")
        sys.exit(1)

if __name__ == "__main__":
    main()