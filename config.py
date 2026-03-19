import os
from pathlib import Path
from datetime import timedelta


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        cleaned = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), cleaned)


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


_load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///scanner.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    SCANNER_API_URL = os.environ.get("SCANNER_API_URL")
    SCANNER_API_TIMEOUT = float(os.environ.get("SCANNER_API_TIMEOUT", "10"))
    SCANNER_API_SOAP_ACTION = os.environ.get("SCANNER_API_SOAP_ACTION")
    SCANNER_TESTING = _as_bool(os.environ.get("SCANNER_TESTING"), default=False)
