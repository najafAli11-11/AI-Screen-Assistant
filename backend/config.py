from app.core.config import SUPPORTED_LANGUAGES, Settings, get_settings, settings

BASE_DIR = __import__("pathlib").Path(__file__).parent

__all__ = ["BASE_DIR", "SUPPORTED_LANGUAGES", "Settings", "get_settings", "settings"]
