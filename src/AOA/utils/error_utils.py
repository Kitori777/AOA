import traceback
from datetime import datetime
from pathlib import Path

from AOA.config import LOGS_DIR

LOGS_DIR.mkdir(parents=True, exist_ok=True)


def format_exception_trace(exc: Exception) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def write_exception_log(context: str, exc: Exception) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"error_{timestamp}.log"

    content = f"[{datetime.now().isoformat()}]\nContext: {context}\n\n{format_exception_trace(exc)}"

    log_path.write_text(content, encoding="utf-8")
    return log_path
