import argparse
import json
import logging
import sys
from datetime import datetime, timedelta

import pandas as pd

from src.reports import (
    spending_by_category,
    spending_by_weekday,
    spending_by_workday,
)
from src.services import (
    investment_bank,
    phone_number_search,
    search_transactions,
    transfers_to_individuals,
)
from src.utils import (
    get_transactions,
    cashback_categories,
)
from src.views import main_page, events_page

logger = logging.getLogger(__name__)

DATE_COL = "Дата операции"


def load_dataframe() -> pd.DataFrame:
    """Читает транзакции и возвращает их в виде датафрейма."""
    try:
        records = get_transactions()
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)
    except Exception as e:
        logger.error("Не удалось загрузить DataFrame: %s", e)
        raise


def month_bounds(date_str: str) -> tuple:
    """Возвращает (начало месяца, конец месяца) по строке с датой."""
    # Берем только первые 10 символов (YYYY-MM-DD), если время есть
    dt_str = date_str[:10]
    dt = datetime.strptime(dt_str, "%Y-%m-%d")
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if dt.month == 12:
        first_next = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        first_next = dt.replace(month=dt.month + 1, day=1)
    end = first_next - timedelta(seconds=1)
    return start, end


def top_recipients_json(items: list) -> str:
    """Агрегирует переводы и возвращает топ-5 получателей JSON-строкой."""
    totals = {}
    for item in items:
        # Защита: если нет recipient, пропускаем
        rec = item.get("recipient")
        if not rec:
            continue
        info = totals.setdefault(rec, {"total": 0.0, "count": 0})
        info["total"] += float(item.get("amount", 0))
        info["count"] += 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1]["total"], reverse=True)
    top = []
    for name, info in ranked[:5]:
        top.append({
            "recipient": name,
            "total": round(info["total"], 2),
            "count": info["count"],
        })
    return json.dumps(top, ensure_ascii=False, indent=2)


def run(command: str, args: argparse.Namespace) -> str | float:
    """Выполняет выбранную команду и возвращает результат."""

    # --- ГЛАВНАЯ СТРАНИЦА ---
    if command == "main":
        date_val = args.date if args.date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return main_page(date_val)

    # --- СОБЫТИЯ ---
    if command == "events":
        date_val = args.date if args.date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return events_page(date_val, period=args.period)

    # --- CASHBACK ---
    if command == "cashback":
        try:
            year = int(args.year)
            month = int(args.month)
        except (ValueError, TypeError) as e:
            logger.error("--year и --month должны быть целыми числами. Ошибка: %s", e)
            raise ValueError("--year и --month должны быть числами (например, --year 2024 --month 7)")

        df = load_dataframe()
        if df.empty:
            logger.warning("Нет транзакций для расчёта кешбэка")
            return json.dumps([], ensure_ascii=False, indent=2)

        if DATE_COL not in df.columns:
            logger.error(f"Колонка '{DATE_COL}' не найдена. Доступные: {list(df.columns)}")
            return json.dumps([], ensure_ascii=False, indent=2)

        df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
        df = df.dropna(subset=[DATE_COL])

        df_filtered = df[(df[DATE_COL].dt.year == year) & (df[DATE_COL].dt.month == month)]

        if df_filtered.empty:
            logger.info(f"Нет транзакций за {year}-{month:02d}")
            return json.dumps([], ensure_ascii=False, indent=2)

        result = cashback_categories(df_filtered)
        return json.dumps(result, ensure_ascii=False, indent=2)

    # --- INVEST ---
    if command == "invest":
        transactions = []
        for record in get_transactions():
            dt_val = record.get(DATE_COL)
            if isinstance(dt_val, datetime):
                dt_str = dt_val.strftime("%Y-%m-%d")
            else:
                dt_str = str(dt_val)[:10] if dt_val else ""

            amount = record.get("Сумма операции", record.get("Сумма в валюте счёта", 0))
            transactions.append({"Дата операции": dt_str, "Сумма операции": amount})
        return investment_bank(args.month, transactions, args.limit)

    # --- TRANSFERS / RECIPIENTS ---
    if command == "transfers":
        if args.date:
            start, end = month_bounds(args.date)
            return transfers_to_individuals(get_transactions(), start, end)
        return transfers_to_individuals(get_transactions())

    if command == "recipients":
        if not args.date:
            # Если даты нет, берем текущую
            args.date = datetime.now().strftime("%Y-%m-%d 00:00:00")
        start, end = month_bounds(args.date)
        filtered = transfers_to_individuals(get_transactions(), start, end)
        try:
            json_data = json.loads(filtered)
            return top_recipients_json(json_data)
        except json.JSONDecodeError:
            logger.error("Не удалось распарсить результат transfers_to_individuals")
            return filtered

    # --- SEARCH / PHONES ---
    if command == "search":
        return search_transactions(args.query, get_transactions())

    if command == "phones":
        return phone_number_search(get_transactions())

    # --- ОТЧЕТЫ (ТАБЛИЦЫ) ---
    df = load_dataframe()
    if command == "category":
        res = spending_by_category(df, args.category, args.date)
        return res.to_string(index=False) if isinstance(res, pd.DataFrame) else str(res)

    if command == "weekday":
        res = spending_by_weekday(df, args.date)
        return res.to_string(index=False) if isinstance(res, pd.DataFrame) else str(res)

    if command == "workday":
        res = spending_by_workday(df, args.date)
        return res.to_string(index=False) if isinstance(res, pd.DataFrame) else str(res)

    raise ValueError(f"Неизвестная команда: {command}")


def command_needs_date(command: str) -> bool:
    return command in ("main", "events", "recipients", "category", "weekday", "workday")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Веб-приложение «Анализ транзакций»")
    parser.add_argument(
        "command",
        choices=[
            "main", "events", "cashback", "invest", "transfers",
            "recipients", "search", "phones", "category",
            "weekday", "workday"
        ],
    )
    parser.add_argument(
        "date_pos",
        nargs="?",
        default=None,
        help="Дата позицией: YYYY-MM-DD HH:MM:SS",
    )
    parser.add_argument("--date", dest="date_opt", default=None, help="Дата опцией")
    parser.add_argument("--period", default="M", help="Диапазон для events: W, M, Y или ALL")
    parser.add_argument("--category", help="Категория для отчёта")
    parser.add_argument("--query", help="Строка поиска для команды search")
    parser.add_argument("--year", type=int, help="Год для сервиса кешбэка")
    parser.add_argument("--month", type=int, help="Месяц для сервиса кешбэка")
    parser.add_argument("--limit", type=int, default=10, help="Лимит записей для invest")

    args = parser.parse_args()

    # Объединяем позиционную дату и опцию
    if args.date_pos:
        args.date = args.date_pos
    elif args.date_opt:
        args.date = args.date_opt
    elif command_needs_date(args.command):
        args.date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return args


def main():
    try:
        args = parse_args()
        result = run(args.command, args)
        print(result)
    except Exception as e:
        logger.exception("Произошла ошибка при выполнении команды: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
