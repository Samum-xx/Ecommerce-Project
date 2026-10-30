import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv

import warnings

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style",
    category=UserWarning,
)


load_dotenv()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_FILE = DATA_DIR / "operations.xlsx"


def get_transactions(filepath: Path | str = DEFAULT_FILE) -> List[Dict[str, Any]]:
    filepath = Path(filepath)
    if not filepath.exists():
        logger.error("Файл не найден: %s", filepath)
        raise FileNotFoundError(f"Файл не найден: {filepath}")

    logger.info("Чтение файла %s", filepath)
    try:
        df = pd.read_excel(filepath, engine="openpyxl")
        transactions: List[Dict[str, Any]] = df.to_dict("records")
        logger.info("Загружено %d транзакций", len(transactions))
        return transactions
    except ImportError:
        logger.error(
            "Не удалось загрузить файл: отсутствует библиотека openpyxl. "
            "Установите: pip install openpyxl"
        )
        raise
    except Exception as e:
        logger.exception("Ошибка чтения файла %s: %s", filepath, e)
        raise


def get_greeting(dt: datetime) -> str:
    hour = dt.hour
    if 5 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"


def get_user_settings() -> dict:
    path = BASE_DIR / "user_settings.json"
    if not path.exists():
        logger.warning("Файл настроек не найден: %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Ошибка парсинга JSON в файле %s: %s", path, e)
        raise
