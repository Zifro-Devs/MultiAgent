"""Orchestrator package — development team coordinator y pipeline de producción."""

from src.orchestrator.pipeline import (
    NullReporter,
    PipelineResult,
    ProgressReporter,
    run_pipeline,
)
from src.orchestrator.quality_gates import (
    GateResult,
    gate_analysis,
    gate_design,
    gate_implementation,
    gate_testing,
)
from src.orchestrator.stack_detector import detect_stack
from src.orchestrator.team import create_dev_team

__all__ = [
    "create_dev_team",
    "run_pipeline",
    "PipelineResult",
    "ProgressReporter",
    "NullReporter",
    "detect_stack",
    "gate_analysis",
    "gate_design",
    "gate_implementation",
    "gate_testing",
    "GateResult",
]
