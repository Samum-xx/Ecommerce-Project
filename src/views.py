import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd

from src.utils import get_transactions

logger = logging.getLogger(__name__)

DATE_COL = "Дата операции"
AMOUNT_COL = "Сумма в валюте счёта"
CATEGORY_COL = "Категория по-умолчанию"


def main_page(data: Optional[List[Dict[str, Any]]] = None) -> str:
    logger.info("Формирование страницы Главная")

    # Если передали данные — используем их, иначе берём из утилиты
    if data is None:
        raw_data = get_transactions()
    else:
        raw_data = data

    # Защита от неправильного типа данных (если вдруг передали строку или None)
    if not isinstance(raw_data, list):
        logger.warning("Получен неверный тип данных в main_page. Используем заглушку.")
        raw_data = get_transactions()

    if not raw_data:
        return json.dumps({
            "expenses": 0.0,
            "income": 0.0,
            "cashback": 0.0,
            "currency_rates": {"USD": 90.0, "EUR": 98.0},
            "stock_prices": {"AAPL": 180.0, "MSFT": 350.0},
        }, ensure_ascii=False)

    df = pd.DataFrame(raw_data)

    # Ищем колонку суммы, если вдруг название отличается
    amount_col = AMOUNT_COL
    if amount_col not in df.columns:
        possible_cols = [c for c in df.columns if "сумма" in str(c).lower()]
        if possible_cols:
            amount_col = possible_cols[0]
        else:
            logger.error(f"Колонка суммы не найдена. Доступные: {list(df.columns)}")
            return json.dumps({"error": "Не найдена колонка суммы"}, ensure_ascii=False)

    amounts = df[amount_col]
    expenses = float(amounts[amounts < 0].sum()) if not amounts[amounts < 0].empty else 0.0
    income = float(amounts[amounts > 0].sum()) if not amounts[amounts > 0].empty else 0.0
    cashback = abs(expenses) * 0.05

    result = {
        "expenses": expenses,
        "income": income,
        "cashback": cashback,
        "currency_rates": {
            "USD": 90.0,
            "EUR": 98.0,
        },
        "stock_prices": {
            "AAPL": 180.0,
            "MSFT": 350.0,
        },
    }

    return json.dumps(result, ensure_ascii=False)


def events_page(
    datetime_str: str,
    period: str = "M",
    data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    if period not in ("W", "M", "Y", "ALL"):
        raise ValueError(f"Неподдерживаемый период: {period}")

    logger.info("События для даты %s, диапазон %s", datetime_str, period)

    raw_data = data if data is not None else get_transactions()
    if not isinstance(raw_data, list):
        raw_data = []

    if not raw_data:
        return json.dumps({"events": [], "period": period}, ensure_ascii=False)

    df = pd.DataFrame(raw_data)

    # Ищем колонки, если названия отличаются
    date_col = DATE_COL
    amount_col = AMOUNT_COL
    category_col = CATEGORY_COL

    if date_col not in df.columns:
        date_candidates = [c for c in df.columns if "дата" in str(c).lower()]
        if date_candidates:
            date_col = date_candidates[0]

    if amount_col not in df.columns:
        amount_candidates = [c for c in df.columns if "сумма" in str(c).lower()]
        if amount_candidates:
            amount_col = amount_candidates[0]

    if category_col not in df.columns:
        category_candidates = [c for c in df.columns if "категор" in str(c).lower()]
        if category_candidates:
            category_col = category_candidates[0]

    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    filtered_df = df
    if (
        not df.empty
        and date_col in df.columns
        and pd.api.types.is_datetime64_any_dtype(df[date_col])
    ):
        if period == "W":
            start = dt - pd.Timedelta(days=7)
            end = dt
        elif period == "M":
            start = pd.Timestamp(dt).replace(day=1)
            next_month = start + pd.offsets.MonthBegin(1)
            end = next_month - pd.Timedelta(seconds=1)
        elif period == "Y":
            start = pd.Timestamp(dt).replace(month=1, day=1)
            next_year = start + pd.offsets.YearBegin(1)
            end = next_year - pd.Timedelta(seconds=1)
        else:  # ALL
            start = df[date_col].min()
            end = df[date_col].max()

        mask = (df[date_col] >= start) & (df[date_col] <= end)
        filtered_df = df.loc[mask].copy()

    events_list = []
    if category_col in filtered_df.columns and amount_col in filtered_df.columns:
        grouped = filtered_df.groupby(category_col)[amount_col].sum()
        for cat, total in grouped.items():
            events_list.append({
                "category": cat,
                "total": float(total),
                "type": "expense" if total < 0 else "income"
            })

    response = {
        "reference_datetime": datetime_str,
        "period": period,
        "events": events_list,
        "summary_total": float(filtered_df[amount_col].sum())
        if amount_col in filtered_df.columns
        else 0.0,
    }
    return json.dumps(response, ensure_ascii=False)
