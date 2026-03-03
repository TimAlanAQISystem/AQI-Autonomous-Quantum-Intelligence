#!/usr/bin/env python3
"""Run the AQI indexing pipeline."""

from pathlib import Path
from aqi_indexer.orchestrator.run_all import PipelineOrchestrator, PipelineConfig

def main():
    config = PipelineConfig(root=Path('.'), output_root=Path('.'))
    orchestrator = PipelineOrchestrator(config)
    orchestrator.run()
    print("Pipeline completed successfully")

if __name__ == "__main__":
    main()