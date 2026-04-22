import customtkinter as ctk

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

        self.model_vars = {
            "Quality": ctk.BooleanVar(value=True),
            "Delay": ctk.BooleanVar(value=False),
            "Schedule": ctk.BooleanVar(value=False),
            "MT": ctk.BooleanVar(value=True),
            "MO": ctk.BooleanVar(value=True),
            "MZO": ctk.BooleanVar(value=True),
            "GENETIC": ctk.BooleanVar(value=True),
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
