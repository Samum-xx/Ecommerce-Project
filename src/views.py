"""Веб-страницы «Главная» и «События»: генерация JSON-ответов."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import get_greeting, get_transactions, get_user_settings

load_dotenv()

logger = logging.getLogger(__name__)

CARD_COL = "Номер карты"
DATE_COL = "Дата операции"
AMOUNT_COL = "Сумма в валюте счёта"
CATEGORY_COL = "Категория по-умолчанию"
DESC_COL = "Описание"

SPECIAL_CATEGORIES = ("Наличные", "Переводы")


def filter_by_period(df: pd.DataFrame, dt: datetime) -> pd.DataFrame:
    """Оставляет транзакции с начала месяца входящей даты по саму дату включительно."""
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mask = (df[DATE_COL] >= start) & (df[DATE_COL] <= dt)
    return df.loc[mask].copy()


def cards_stats(transactions: List[Dict[str, Any]], dt: datetime) -> List[Dict[str, Any]]:
    """По каждой карте: общая сумма расходов и кешбэк (1 рубль на каждые 100)."""
    df = pd.DataFrame(transactions)
    df = filter_by_period(df, dt)
    df = df[df[AMOUNT_COL] < 0]  # только расходы
    result = []
    for card, group in df.groupby(CARD_COL):
        total = abs(group[AMOUNT_COL].sum())
        result.append(
            {
                "last_digits": str(card).replace("*", "")[-4:],
                "total_spent": round(total, 2),
                "cashback": round(total / 100, 2),
            }
        )
    return result


def top_transactions(
    transactions: List[Dict[str, Any]], dt: datetime, n: int = 5
) -> List[Dict[str, Any]]:
    """Топ-5 транзакций по убыванию суммы платежа (amount)."""
    df = pd.DataFrame(transactions)
    df = filter_by_period(df, dt)
    top = df.sort_values(AMOUNT_COL, ascending=False).head(n)
    return [
        {
            "date": row[DATE_COL].strftime("%d.%m.%Y"),
            "amount": row[AMOUNT_COL],
            "category": row[CATEGORY_COL],
            "description": row[DESC_COL],
        }
        for _, row in top.iterrows()
    ]


def get_currency_rates(currencies: List[str]) -> List[Dict[str, Any]]:
    """Получает курсы валют через бесплатный API open.er-api.com.

    Возвращает список {currency, rate}, где rate — рублей за единицу валюты.
    При ошибке API — пустой список.
    """
    rates: List[Dict[str, Any]] = []
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        response.raise_for_status()
        base_rates = response.json().get("rates", {})
        rub_per_usd = base_rates.get("RUB")
        if not rub_per_usd:
            logger.warning("Курс RUB не найден в ответе API")
            return rates
        for currency in currencies:
            rate = base_rates.get(currency)
            if rate:
                rub_per_unit = rub_per_usd / rate  # рублей за единицу валюты
                rates.append({"currency": currency, "rate": round(rub_per_unit, 2)})
            else:
                logger.warning("Курс для валюты %s не найден", currency)
    except requests.RequestException:
        logger.exception("Ошибка запроса курсов валют")
    return rates


def get_stock_prices(stocks: List[str]) -> List[Dict[str, Any]]:
    """Получает цены акций через публичный API Yahoo Finance (без ключа).

    Возвращает список {stock, price}. При ошибке API — пустой список.
    """
    prices: List[Dict[str, Any]] = []
    for stock in stocks:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock}"
        try:
            response = requests.get(
                url,
                params={"interval": "1d", "range": "5d"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json().get("chart", {}).get("result", [])
            if result:
                price = result[0]["meta"].get("regularMarketPrice")
                if price is not None:
                    prices.append({"stock": stock, "price": round(float(price), 2)})
                    continue
            logger.warning("Цена для акции %s не найдена", stock)
        except requests.RequestException:
            logger.exception("Ошибка запроса цены акции %s", stock)
    return prices


def main_page(datetime_str: str) -> str:
    """Главная функция: принимает 'YYYY-MM-DD HH:MM:SS', возвращает JSON-строку."""
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    logger.info("Главная страница для даты %s", datetime_str)

    transactions = get_transactions()
    settings = get_user_settings()
    currencies: List[str] = settings.get("user_currencies", [])
    stocks: List[str] = settings.get("user_stocks", [])

    response = {
        "greeting": get_greeting(dt),
        "cards": cards_stats(transactions, dt),
        "top_transactions": top_transactions(transactions, dt),
        "currency_rates": get_currency_rates(currencies),
        "stock_prices": get_stock_prices(stocks),
    }
    return json.dumps(response, ensure_ascii=False, indent=2)


def get_period_range(period: str, dt: datetime) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Начало и конец диапазона для страницы «События».

    W — неделя даты (с понедельника), M — месяц, Y — год.
    """
    if period == "W":
        start = dt - pd.Timedelta(days=dt.dayofweek)
    elif period == "Y":
        start = dt.replace(month=1, day=1)
    else:  # M — по умолчанию
        start = dt.replace(day=1)
    return (
        pd.Timestamp(start.replace(hour=0, minute=0, second=0, microsecond=0)),
        pd.Timestamp(dt),
    )


def top_categories(frame: pd.DataFrame, top_n: int = 7) -> List[Dict[str, Any]]:
    """Топ-N категорий по убыванию суммы, остальные — в «Остальное»."""
    if frame.empty:
        return []
    sums = frame.groupby(CATEGORY_COL)["amount"].sum().sort_values(ascending=False)
    items = [
        {"category": category, "amount": round(value)}
        for category, value in sums.head(top_n).items()
    ]
    rest = sums.iloc[top_n:].sum()
    if rest:
        items.append({"category": "Остальное", "amount": int(round(rest))})
    return items


def events_page(
    datetime_str: str,
    period: str = "M",
    data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Страница «События»: JSON с расходами, поступлениями, курсами и акциями.

    period: 'W' — неделя, 'M' — месяц (по умолчанию), 'Y' — год,
    'ALL' — все данные до указанной даты.
    """
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    if period not in ("W", "M", "Y", "ALL"):
        raise ValueError(f"Неподдерживаемый период: {period}")
    logger.info("События для даты %s, диапазон %s", datetime_str, period)

    df = pd.DataFrame(data if data is not None else get_transactions())

    if df.empty:
        response = {
            "expenses": {"total_amount": 0, "main": [], "transfers_and_cash": []},
            "income": {"total_amount": 0, "main": []},
        }
        return json.dumps(response, ensure_ascii=False, indent=2)

    if period == "ALL":
        mask = df[DATE_COL] <= pd.Timestamp(dt)
    else:
        start, end = get_period_range(period, dt)
        mask = (df[DATE_COL] >= start) & (df[DATE_COL] <= end)
    df = df.loc[mask]

    expenses_df = df[df[AMOUNT_COL] < 0].copy()
    expenses_df["amount"] = expenses_df[AMOUNT_COL].abs()
    income_df = df[df[AMOUNT_COL] > 0].copy()
    income_df["amount"] = income_df[AMOUNT_COL]

    main_expenses = expenses_df[~expenses_df[CATEGORY_COL].isin(SPECIAL_CATEGORIES)]
    special_expenses = expenses_df[expenses_df[CATEGORY_COL].isin(SPECIAL_CATEGORIES)]

    settings = get_user_settings()
    response = {
        "expenses": {
            "total_amount": int(round(expenses_df["amount"].sum())),
            "main": top_categories(main_expenses),
            "transfers_and_cash": top_categories(special_expenses),
        },
        "income": {
            "total_amount": int(round(income_df["amount"].sum())),
            "main": top_categories(income_df),
        },
        "currency_rates": get_currency_rates(settings.get("user_currencies", [])),
        "stock_prices": get_stock_prices(settings.get("user_stocks", [])),
    }
    return json.dumps(response, ensure_ascii=False, indent=2)
