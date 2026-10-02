from AOA.platform import bootstrap_user_data, resolve_app_paths

APP_PATHS = resolve_app_paths()
bootstrap_user_data(APP_PATHS)

# Compatibility aliases used by the existing services. In a source checkout
# these keep the portable repository layout; in a packaged build they point to
# writable per-user directories.
BASE_DIR = APP_PATHS.user_root
RESOURCE_ROOT = APP_PATHS.resource_root
CONFIG_DIR = APP_PATHS.config_root
DATA_DIR = APP_PATHS.data_dir
MODELS_DIR = APP_PATHS.models_dir
DOCS_DIR = APP_PATHS.docs_dir
LOGS_DIR = APP_PATHS.logs_dir
CACHE_DIR = APP_PATHS.cache_dir
ASSETS_DIR = APP_PATHS.assets_dir
ASSISTANT_ASSETS_DIR = ASSETS_DIR / "assistant"

MODEL_FILE = MODELS_DIR / "model.pkl"
DEFAULT_RESULT_FILE = DATA_DIR / "wynik_priority.csv"

FULL_DATA_FILE = DATA_DIR / "production_data.csv"
TRAIN_DATA_FILE = DATA_DIR / "train_data.csv"
TEST_DATA_FILE = DATA_DIR / "test_data.csv"

GUIDE_FILE = DOCS_DIR / "guide.md"
THEORY_FILE = DOCS_DIR / "theory.md"
