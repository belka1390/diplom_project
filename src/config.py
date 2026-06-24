"""
Модуль конфигурации проекта.
Загружает настройки из .env файла.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка .env из корня проекта
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Централизованное хранилище настроек"""
    
    # Пути
    PROJECT_ROOT = PROJECT_ROOT
    DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
    DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
    LOGS_DIR = PROJECT_ROOT / "logs"
    REPORTS_DIR = PROJECT_ROOT / "reports"
    
    # Настройки парсера
    SEARCH_URL = os.getenv("SEARCH_URL")
    CSV_FILENAME = os.getenv("CSV_FILENAME", "tenders_data.csv")
    DOCS_DIR = DATA_RAW_DIR / os.getenv("DOCS_DIR", "downloaded_docs")
    MAX_PAGES = int(os.getenv("MAX_PAGES", 3))
    MAX_TENDERS = int(os.getenv("MAX_TENDERS", 5))
    HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"
    
    # Настройки YandexGPT
    YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
    YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
    YANDEX_GPT_MODEL = os.getenv("YANDEX_GPT_MODEL", "yandexgpt-lite")
    
    @classmethod
    def validate(cls):
        """Проверка обязательных настроек"""
        errors = []
        if not cls.SEARCH_URL:
            errors.append("SEARCH_URL не задан в .env")
        if not cls.YANDEX_API_KEY:
            errors.append("YANDEX_API_KEY не задан в .env")
        if not cls.YANDEX_FOLDER_ID:
            errors.append("YANDEX_FOLDER_ID не задан в .env")
        
        if errors:
            raise ValueError("Ошибки конфигурации:\n" + "\n".join(errors))
        
        # Создание необходимых директорий
        for dir_path in [cls.DATA_RAW_DIR, cls.DATA_PROCESSED_DIR, cls.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)