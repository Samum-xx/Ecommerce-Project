"""Страница «Отчёты»: траты по категории, по дням недели,
рабочий/выходной день."""
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from src.decorators import save_report_to_file

logger = logging.getLogger(__name__)

DATE_COL = "Дата операции"
AMOUNT_COL = "Сумма в валюте счёта"
CATEGORY_COL = "Категория по-умолчанию"


def _parse_date(date: Optional[str]) -> datetime:
    """Разбирает дату из строки; без строки берёт текущий момент."""
    if date is None:
        return datetime.now()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            continue
    raise ValueError(f"Неподдерживаемый формат даты: {date}")


def _expenses_window(df: pd.DataFrame, end: datetime, months: int = 3) -> pd.DataFrame:
    """Расходы за последние `months` месяцев: с 1-го числа месяца-минус-(months-1) до end."""
    start = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0) \
        - pd.DateOffset(months=months - 1)
    mask = (
        (df[AMOUNT_COL] < 0)
        & (df[DATE_COL] >= start)
        & (df[DATE_COL] <= end)
    )
    return df.loc[mask].copy()


@save_report_to_file()
def spending_by_category(
    transactions: pd.DataFrame, category: str, date: Optional[str] = None
) -> pd.DataFrame:
    """Траты по категории за последние три месяца от переданной даты."""
    end = _parse_date(date)
    df = _expenses_window(transactions, end)
    df = df[df[CATEGORY_COL] == category]
    result = df.groupby(df[DATE_COL].dt.to_period("M")).agg(
        spent=(AMOUNT_COL, lambda s: round(abs(s.sum()), 2)),
        operations=(AMOUNT_COL, "count"),
    ).reset_index()
    result.columns = ["month", "spent", "operations"]
    result["month"] = result["month"].astype(str)
    logger.info("Отчёт по категории %s на %s: %d строк", category, end, len(result))
    return result


@save_report_to_file()
def spending_by_weekday(
    transactions: pd.DataFrame, date: Optional[str] = None
) -> pd.DataFrame:
    """Средние траты по дням недели за последние три месяца."""
    end = _parse_date(date)
    df = _expenses_window(transactions, end)
    if df.empty:
        return pd.DataFrame(columns=["weekday", "average_spent"])
    names = {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг",
             4: "Пятница", 5: "Суббота", 6: "Воскресенье"}
    df = df.assign(weekday=df[DATE_COL].dt.day_of_week.map(names))
    result = df.groupby("weekday").agg(
        average_spent=(AMOUNT_COL, lambda s: round(abs(s).mean(), 2))
    ).reset_index()
    order = list(names.values())
    result = result.set_index("weekday").reindex(order).reset_index()
    return result


@save_report_to_file()
def spending_by_workday(
    transactions: pd.DataFrame, date: Optional[str] = None
) -> pd.DataFrame:
    """Средние траты в рабочие и выходные дни за последние три месяца."""
    end = _parse_date(date)
    df = _expenses_window(transactions, end)
    if df.empty:
        return pd.DataFrame(columns=["day_type", "average_spent"])
    df = df.assign(
        day_type=df[DATE_COL].dt.day_of_week.apply(
            lambda w: "Выходной" if w >= 5 else "Рабочий"
        )
    )
    result = df.groupby("day_type").agg(
        average_spent=(AMOUNT_COL, lambda s: round(abs(s).mean(), 2))
    ).reset_index()
    return result
