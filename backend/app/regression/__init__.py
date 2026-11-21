from .adapters import PLATFORM_LABELS, Adapter, Backend, SimulationBackend, UnsupportedPlatform
from .collector import make_event, metric_from, persist_events, snapshot_events
from .config import RegressionConfig, Thresholds, from_file, from_mapping, with_repeats
from .dsl import all_scenarios, by_id, core_scenarios, matrix, validate_scenario
from .model import (
    BASELINE, CANDIDATE, NOT_REGRESSED, MINOR_REGRESSION, SEVERE_REGRESSION,
    UNDECIDABLE, VERDICTS, Defect, Environment, Event, GateResult, ProbeSnapshot,
    RegressionResult, RunOutcome, RunSpec, Scenario, Step, VerdictRow, Version,
)
from .orchestrator import Orchestrator
from .probes import evidence_complete, run_checks
from .reports import FILE_NAMES, render_all
from .verdict import decide, evidence_link

__all__ = [
    "PLATFORM_LABELS", "Adapter", "Backend", "SimulationBackend", "UnsupportedPlatform",
    "make_event", "metric_from", "persist_events", "snapshot_events",
    "RegressionConfig", "Thresholds", "from_file", "from_mapping", "with_repeats",
    "all_scenarios", "by_id", "core_scenarios", "matrix", "validate_scenario",
    "BASELINE", "CANDIDATE", "NOT_REGRESSED", "MINOR_REGRESSION",
    "SEVERE_REGRESSION", "UNDECIDABLE", "VERDICTS",
    "Defect", "Environment", "Event", "GateResult", "ProbeSnapshot",
    "RegressionResult", "RunOutcome", "RunSpec", "Scenario", "Step", "VerdictRow", "Version",
    "Orchestrator", "evidence_complete", "run_checks", "FILE_NAMES", "render_all",
    "decide", "evidence_link",
]
