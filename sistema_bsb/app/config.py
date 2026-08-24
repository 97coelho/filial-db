import os
from pathlib import Path


def default_database_url():
    data_dir = Path(os.environ.get("FILIAL_BSB_DATA_DIR", Path.home() / ".local/share/filial-bsb"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'filial_bsb.db'}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "desenvolvimento-apenas")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", default_database_url())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    API_TOKEN = os.environ.get("API_TOKEN", "")
    ITEMS_PER_PAGE = 25


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
