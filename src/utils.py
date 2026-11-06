import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Путь к Excel: сначала пробуем из .env, если нет — берём operations.xlsx из текущей папки (src)
FILE_PATH = os.getenv(
    "EXCEL_PATH",
    os.path.join(os.path.dirname(__file__), "operations.xlsx"),
)


def get_greeting(current_time: datetime) -> str:
    """Возвращает приветствие по времени суток."""
    hour = current_time.hour
    if 6 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def get_user_settings() -> Dict[str, Any]:
    logger.debug("Возвращаем базовые настройки пользователя.")
    return {
        "currency": "RUB",
        "locale": "ru_RU",
        "default_period": "M",
        "show_hidden_categories": False,
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "MSFT"],
    }


def get_transactions() -> List[Dict[str, Any]]:
    """
    Загружает транзакции из operations.xlsx и возвращает как список словарей.
    Если файл не найден — возвращает тестовую заглушку.
    """
    if not os.path.exists(FILE_PATH):
        logger.warning(f"Файл {FILE_PATH} не найден. Используется тестовая заглушка.")
        return [
            {
                "Дата операции": datetime(2024, 7, 1, 10, 0, 0),
                "Сумма в валюте счёта": -1500.0,
                "Категория по-умолчанию": "Продукты",
                "Описание": "Покупка в супермаркете",
                "Номер карты": "****1234",
            },
            {
                "Дата операции": datetime(2024, 7, 5, 14, 30, 0),
                "Сумма в валюте счёта": -800.0,
                "Категория по-умолчанию": "Транспорт",
                "Описание": "Поездка на такси",
                "Номер карты": "****5678",
            },
            {
                "Дата операции": datetime(2024, 7, 10, 9, 15, 0),
                "Сумма в валюте счёта": 5000.0,
                "Категория по-умолчанию": "Зарплата",
                "Описание": "Начисление зарплаты",
                "Номер карты": "****1234",
            },
            {
                "Дата операции": datetime(2024, 7, 12, 11, 20, 0),
                "Сумма в валюте счёта": -350.0,
                "Категория по-умолчанию": "Аптеки",
                "Описание": "Лекарства",
                "Номер карты": "****5678",
            },
            {
                "Дата операции": datetime(2024, 7, 15, 16, 45, 0),
                "Сумма в валюте счёта": -2000.0,
                "Категория по-умолчанию": "Одежда",
                "Описание": "Футболка и джинсы",
                "Номер карты": "****1234",
            },
            {
                "Дата операции": datetime(2024, 7, 18, 13, 10, 0),
                "Сумма в валюте счёта": -400.0,
                "Категория по-умолчанию": "Наличные",
                "Описание": "Снятие наличных",
                "Номер карты": "****5678",
            },
            {
                "Дата операции": datetime(2024, 7, 20, 17, 0, 0),
                "Сумма в валюте счёта": -600.0,
                "Категория по-умолчанию": "Переводы",
                "Описание": "Перевод другу",
                "Номер карты": "****1234",
            },
        ]

    try:
        df = pd.read_excel(FILE_PATH)
        df.columns = df.columns.str.strip()

        rename_map = {
            "card_number": "Номер карты",
            "date": "Дата операции",
            "amount": "Сумма в валюте счёта",
            "category": "Категория по-умолчанию",
            "description": "Описание",
        }
        existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=existing_cols)

        if "Дата операции" in df.columns:
            df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")

        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Ошибка при чтении Excel: {e}")
        return []


def cashback_categories(df: pd.DataFrame) -> list[dict]:
    AMOUNT_COL = "Сумма в валюте счёта"
    CATEGORY_COL = "Категория по-умолчанию"

    # Оставляем только расходы (отрицательные суммы)
    expenses_df = df[df[AMOUNT_COL] < 0].copy()
    if expenses_df.empty:
        return []

    grouped = expenses_df.groupby(CATEGORY_COL)[AMOUNT_COL].sum()

    result = []
    for cat, total in grouped.items():
        # total уже отрицательный, поэтому берём abs для кешбэка
        cashback = abs(total) * 0.05
        result.append({
            "category": cat,
            "total_spent": float(total),
            "cashback": round(cashback, 2),
            "rate": "5%"
        })

    # Сортируем по кешбэку (по убыванию)
    result.sort(key=lambda x: x["cashback"], reverse=True)

    # Возвращаем только топ‑3
    return result[:3]
