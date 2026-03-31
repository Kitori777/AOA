import traceback
from datetime import datetime
from pathlib import Path

from AOA.config import BASE_DIR


LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def format_exception_trace(exc: Exception) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def write_exception_log(context: str, exc: Exception) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"error_{timestamp}.log"

    content = (
        f"[{datetime.now().isoformat()}]\n"
        f"Context: {context}\n\n"
        f"{format_exception_trace(exc)}"
    )

    log_path.write_text(content, encoding="utf-8")
    return log_path
