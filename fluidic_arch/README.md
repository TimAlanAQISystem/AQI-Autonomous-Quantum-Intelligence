# Fluidic Architecture

This folder contains the complete modular implementation of the Fluidic Intelligence Architecture - a production-ready system for autonomous AI orchestration using vector field analysis, DMA agents, and form-based pattern generation.

## Overview

The Fluidic Architecture implements an intelligence paradigm based on fluid dynamics principles:
- **DMAs (Dynamic Micro Agents)**: Autonomous agents operating in vector fields
- **Signal Fields**: Discrete vector spaces with divergence and curl calculations
- **Forms**: Pattern templates for repeatable intelligence workflows
- **Containers**: Isolated execution environments with boundary enforcement
- **MEngine**: Governance engine with axioms and constraints

## Project Structure

```
fluidic_arch/
├── __init__.py          # Package initialization
├── config.py            # Global configuration and enums
├── mengine.py           # Governance engine with rules and validation
├── containers.py        # Container lifecycle and self-store patterns
├── forms.py             # Form types and pattern serialization
├── fluid.py             # DMA agents, MCI spawner, signal fields, boundary enforcement
├── aqi.py               # Orchestrator coordinating all components
├── lattice.py           # Substrate structure (placeholder for future expansion)
├── metrics.py           # Health monitoring and performance tracking
├── main.py              # Example run demonstrating the system
└── diagnostics.log      # Sample log file for connector testing
```

## Key Features

- **Modular Design**: Clean separation of concerns across 9 modules
- **Real Connectors**: Local file system integration (log reading)
- **Boundary Enforcement**: DMAs strictly respect container limits
- **Pattern Reuse**: Forms cached in container self-store
- **Governance**: MEngine validates all operations against axioms
- **Health Monitoring**: Comprehensive metrics tracking system performance
- **Production Ready**: Error handling, logging, resource management

## Running the System

```bash
cd fluidic_arch
python main.py
```

Expected output demonstrates:
- Container activation
- DMA spawning and decision-making based on mass/divergence/curl
- Boundary-enforced log reading (5 lines from `diagnostics.log`)
- Form pattern creation and reuse from container self-store
- **Metrics snapshots** showing DMA counts, execution times, form usage, and system health

## Metrics & Monitoring

The system includes comprehensive health tracking:

- **DMA Metrics**: Spawn/completion/termination/error counts, average execution times
- **Form Metrics**: Creation vs reuse statistics
- **Governance**: MEngine rule violation tracking
- **Container Health**: Status and error logging per container
- **Performance**: Run duration and timing analysis

Call `Metrics.snapshot()` to get a complete system health report.

## Version History

- **v0.1**: Initial concept and skeleton
- **v0.2**: Working implementation with basic functionality
- **v0.3**: Production enhancements (error handling, monitoring, FormType enum)
- **v1.0**: Modular architecture with real connectors and boundary enforcement

## Future Enhancements

- ✅ **Metrics module** for health snapshots and violation tracking (implemented)
- Second container (Risk_Container) for multi-container orchestration
- Real API integrations (Twilio, external services)
- Lattice connectivity for distributed operation
- Persistent storage for patterns and system state