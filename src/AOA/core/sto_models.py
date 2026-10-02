"""Compatibility facade for the modular production-optimization engine.

New code should import from :mod:`AOA.core.optimization`. This module keeps the
public 0.10.0 API stable for the desktop UI, CLI and existing integrations.
"""

from AOA.core.optimization.evaluation import evaluate_sequence
from AOA.core.optimization.heuristics.classic import (
    sequence_cr,
    sequence_edd_spt,
    sequence_lpt_edd,
    sequence_mo,
    sequence_mt,
    sequence_mzo,
    sequence_slack,
    sequence_spt_edd,
)
from AOA.core.optimization.heuristics.resource import (
    sequence_component_ready_edd,
    sequence_eco_waste,
)
from AOA.core.optimization.heuristics.search import (
    sequence_genetic,
    sequence_local_search,
    sequence_mopt,
    sequence_neh,
    sequence_random_restart,
)
from AOA.core.optimization.models import Job, dataframe_to_jobs, parse_jobs
from AOA.core.optimization.objectives import (
    OPTIMIZATION_OBJECTIVES,
)
from AOA.core.optimization.results import (
    apply_sto_result_to_dataframe,
    build_sto_report,
)
from AOA.core.optimization.runner import run_selected_sto_models

__all__ = [
    "Job",
    "OPTIMIZATION_OBJECTIVES",
    "apply_sto_result_to_dataframe",
    "build_sto_report",
    "dataframe_to_jobs",
    "evaluate_sequence",
    "parse_jobs",
    "run_selected_sto_models",
    "sequence_component_ready_edd",
    "sequence_cr",
    "sequence_eco_waste",
    "sequence_edd_spt",
    "sequence_genetic",
    "sequence_local_search",
    "sequence_lpt_edd",
    "sequence_mo",
    "sequence_mopt",
    "sequence_mt",
    "sequence_mzo",
    "sequence_neh",
    "sequence_random_restart",
    "sequence_slack",
    "sequence_spt_edd",
]
