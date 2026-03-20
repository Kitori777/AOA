from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"

DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)

MODEL_FILE = MODELS_DIR / "model.pkl"
DEFAULT_RESULT_FILE = DATA_DIR / "wynik_priority.csv"

FULL_DATA_FILE = DATA_DIR / "production_data.csv"
TRAIN_DATA_FILE = DATA_DIR / "train_data.csv"
TEST_DATA_FILE = DATA_DIR / "test_data.csv"

GUIDE_FILE = DOCS_DIR / "guide.md"
THEORY_FILE = DOCS_DIR / "theory.md"
