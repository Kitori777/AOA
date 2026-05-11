# ruff: noqa: F401
"""Public service facade.

Concrete implementations live in focused modules in this package. The facade is
kept only for stable imports such as ``from AOA.core import services``.
"""

from AOA.config import DATA_DIR, MODELS_DIR
from AOA.core.data_generation import generate_production_data
from AOA.core.data_io import load_csv, save_csv
from AOA.core.dataset_ops import split_train_test
from AOA.core.evaluation import (
    append_metrics_row,
    calculate_classification_metrics,
    calculate_model_training_metrics,
    calculate_regression_metrics,
    fill_missing_values,
    format_training_metrics,
    transform_numeric_columns,
)
from AOA.core.models import load_model_pack, save_model_pack, train_selected_models

from .analysis import prepare_results_analysis
from .common import (
    ML_MODEL_NAMES,
    STO_MODEL_NAMES,
    parse_generation_config,
    split_selected_models,
)
from .files import (
    build_model_filename,
    build_result_filename,
    build_sto_model_filename,
    sanitize_filename,
)
from .io_ops import (
    generate_and_store_datasets,
    generate_and_store_datasets_from_config,
    load_and_prepare_visual_file,
    load_training_data,
)
from .sto import analyze_sto_models, solve_sto_with_saved_model
from .summary import (
    build_dataframe_preview_text,
    build_main_page_status,
    build_main_page_summary,
)
from .training import solve_models_flow, train_models_flow, train_sto_models_flow

__all__ = [name for name in globals() if not name.startswith("_")]
