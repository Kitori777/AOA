import customtkinter as ctk

from AOA.core.mh_models import get_mh_model_specs
from AOA.core.ml_models import get_ml_model_specs

from .config_form import MainPageConfigFormMixin
from .progress_panel import MainPageProgressPanelMixin
from .results_panel import MainPageResultsPanelMixin
from .state import MainPageStateMixin


class MainPage(
    MainPageConfigFormMixin,
    MainPageProgressPanelMixin,
    MainPageResultsPanelMixin,
    MainPageStateMixin,
    ctk.CTkFrame,
):
    def __init__(self, parent):
        super().__init__(parent)
        self.df_train = None
        self.df_test = None
        self.df_full = None
        self.loaded_data_path = None
        self.last_generation_metadata = {}
        self._last_progress_per_model = {}

        self.ml_model_specs = get_ml_model_specs()
        self.mh_model_specs = get_mh_model_specs()
        self.model_vars = {
            **{
                spec.name: ctk.BooleanVar(value=spec.name == "Quality")
                for spec in self.ml_model_specs
            },
            **{
                spec.name: ctk.BooleanVar(value=spec.name in {"MT", "MO", "MZO", "MOPT"})
                for spec in self.mh_model_specs
            },
        }
        self.ksztalt_vars = {
            "kwadrat": ctk.BooleanVar(value=True),
            "trojkat": ctk.BooleanVar(value=True),
            "trapez": ctk.BooleanVar(value=True),
        }
        self.material_vars = {
            "bawelna": ctk.BooleanVar(value=True),
            "mikrofibra": ctk.BooleanVar(value=True),
            "poliester": ctk.BooleanVar(value=True),
            "wiskoza": ctk.BooleanVar(value=True),
        }
        self.n_var = ctk.StringVar(value="5000")
        self.n_machines_var = ctk.StringVar(value="1")
        self.test_size_var = ctk.StringVar(value="0.2")
        self.seed_var = ctk.StringVar(value="42")
        self.prod_min_var = ctk.StringVar(value="1")
        self.prod_max_var = ctk.StringVar(value="48")
        self.deadline_min_var = ctk.StringVar(value="1")
        self.deadline_max_var = ctk.StringVar(value="72")
        self.backend_var = ctk.StringVar(value="classic")
        self.sto_jobs_var = ctk.StringVar(value="Z1,Z2,Z3")
        self.sto_times_var = ctk.StringVar(value="10,20,100")
        self.sto_deadlines_var = ctk.StringVar(value="150,30,110")
        self._build_layout()
        self.render_summary()
        self.render_status()
        self.render_preview()
