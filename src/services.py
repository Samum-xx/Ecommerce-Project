"""Страница «Сервисы»: кешбэк-категории, Инвесткопилка, переводы физлицам."""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils import get_transactions

logger = logging.getLogger(__name__)

DATE_COL = "Дата операции"
AMOUNT_COL = "Сумма в валюте счёта"
CATEGORY_COL = "Категория по-умолчанию"
DESC_COL = "Описание"

# «Имя О.» — имя и первая буква фамилии с точкой (по ТЗ)
PERSON_PATTERN = re.compile(r"[А-ЯЁ][а-яё]+ [А-ЯЁ]\.")


def cashback_categories(
    data: List[Dict[str, Any]], year: int, month: int
) -> str:
    """Анализ выгодных категорий повышенного кешбэка за указанный месяц.

    Принимает данные с транзакциями, год и месяц. Возвращает JSON:
    словарь {категория: сумма кешбэка} по расходам этого месяца.
    """
    df = pd.DataFrame(data)
    if df.empty:
        return json.dumps({}, ensure_ascii=False, indent=2)

    mask = (
        (df[DATE_COL].dt.year == year)
        & (df[DATE_COL].dt.month == month)
        & (df[AMOUNT_COL] < 0)
    )
    df = df.loc[mask]
    if df.empty:
        return json.dumps({}, ensure_ascii=False, indent=2)

    result = df.groupby(CATEGORY_COL)[AMOUNT_COL].sum().abs().div(100).round(2)
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def investment_bank(
    month: str, transactions: List[Dict[str, Any]], limit: int
) -> float:
    """Рассчитывает сумму, которую удалось бы отложить в «Инвесткопилку».

    Транзакции за указанный месяц ('YYYY-MM') округляются вверх до limit,
    разница между округлённой и фактической суммой откладывается.
    """
    total_savings = 0.0
    for tx in transactions:
        dt = datetime.strptime(tx["Дата операции"], "%Y-%m-%d")
        if dt.strftime("%Y-%m") != month:
            continue
        amount = tx["Сумма операции"]
        if amount >= 0:  # копим только с расходов
            continue
        rounded = -(-abs(amount) // limit) * limit
        total_savings += rounded - abs(amount)
    return round(total_savings, 2)


def transfers_to_individuals(
    data: Optional[List[Dict[str, Any]]] = None, period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> str:
    """Переводы физлицам: категория «Переводы», описание в формате «Имя О.».

    Если период не задан — берёт все данные. Возвращает JSON со списком
    {date, amount, recipient}.
    """
    df = pd.DataFrame(data if data is not None else get_transactions())
    if df.empty:
        return json.dumps([], ensure_ascii=False, indent=2)

    df = df[df[CATEGORY_COL] == "Переводы"]
    df = df[df[AMOUNT_COL] < 0]
    if period_start is not None:
        df = df[df[DATE_COL] >= period_start]
    if period_end is not None:
        df = df[df[DATE_COL] <= period_end]
    df = df[df[DESC_COL].astype(str).str.match(PERSON_PATTERN)]

    df = df.sort_values(DATE_COL)
    result: List[Dict[str, Any]] = [
        {
            "date": row[DATE_COL].strftime("%d.%m.%Y"),
            "amount": abs(row[AMOUNT_COL]),
            "recipient": row[DESC_COL],
        }
        for _, row in df.iterrows()
    ]
    return json.dumps(result, ensure_ascii=False, indent=2)


def top_recipients(datetime_str: str, n: int = 5) -> str:
    """Топ получателей переводов физлицам за последний квартал."""
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    raw = transfers_to_individuals(period_start=dt - pd.Timedelta(days=90), period_end=dt)
    data = json.loads(raw)
    if not data:
        return json.dumps([], ensure_ascii=False, indent=2)

    df = pd.DataFrame(data)
    summary = df.groupby("recipient")["amount"].agg(["sum", "count"]).nlargest(n, "sum")
    result: List[Dict[str, Any]] = [
        {"recipient": name, "total": round(row["sum"], 2), "count": int(row["count"])}
        for name, row in summary.iterrows()
    ]
    return json.dumps(result, ensure_ascii=False, indent=2)


PHONE_PATTERN = re.compile(
    r"(?:\+7|8)\D{0,2}\d{3}\D{0,2}"
    r"(?:\d{3}\D{0,2}\d{2}\D{0,2}\d{2}|\d{2}\D{0,2}\d{2}\D{0,2}\d{2})"
)


def search_transactions(
    query: str, data: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Простой поиск: возвращает транзакции с подстрокой в описании или категории.

    Поиск нечувствителен к регистру.
    """
    df = pd.DataFrame(data if data is not None else get_transactions())
    if df.empty:
        return json.dumps([], ensure_ascii=False, indent=2)

    needle = str(query).lower()
    mask = (
        df[DESC_COL].astype(str).str.lower().str.contains(needle, regex=False)
        | df[CATEGORY_COL].astype(str).str.lower().str.contains(needle, regex=False)
    )
    df = df.loc[mask].sort_values(DATE_COL)
    result: List[Dict[str, Any]] = [
        {
            "date": row[DATE_COL].strftime("%d.%m.%Y"),
            "amount": row[AMOUNT_COL],
            "category": row[CATEGORY_COL],
            "description": row[DESC_COL],
        }
        for _, row in df.iterrows()
    ]
    return json.dumps(result, ensure_ascii=False, indent=2)


def phone_number_search(
    data: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Поиск по телефонным номерам: транзакции с мобильными номерами в описании."""
    df = pd.DataFrame(data if data is not None else get_transactions())
    if df.empty:
        return json.dumps([], ensure_ascii=False, indent=2)

    df = df[df[DESC_COL].astype(str).str.contains(PHONE_PATTERN, regex=True)]
    df = df.sort_values(DATE_COL)
    result: List[Dict[str, Any]] = [
        {
            "date": row[DATE_COL].strftime("%d.%m.%Y"),
            "amount": row[AMOUNT_COL],
            "category": row[CATEGORY_COL],
            "description": row[DESC_COL],
        }
        for _, row in df.iterrows()
    ]
    return json.dumps(result, ensure_ascii=False, indent=2)
