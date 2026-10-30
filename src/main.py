"""Точка входа: запуск страниц и сервисов через командную строку.

Примеры запуска:
    python -m src.main main "2024-07-30 18:00:00"
    python -m src.main events "2024-07-30 18:00:00" --period M
    python -m src.main cashback --year 2024 --month 7
    python -m src.main invest --month 2024-07 --limit 50
    python -m src.main transfers "2024-07-30 18:00:00"
    python -m src.main recipients "2024-07-30 18:00:00"
    python -m src.main search "Лента"
    python -m src.main phones
    python -m src.main category --category Переводы "2024-07-30 18:00:00"
    python -m src.main weekday "2024-07-30 18:00:00"
    python -m src.main workday "2024-07-30 18:00:00"
"""
import argparse
import json
import sys
from datetime import datetime, timedelta

import pandas as pd

from src.reports import (
    spending_by_category,
    spending_by_weekday,
    spending_by_workday,
)
from src.services import (
    cashback_categories,
    investment_bank,
    phone_number_search,
    search_transactions,
    transfers_to_individuals,
)
from src.utils import get_transactions
from src.views import events_page, main_page

DATE_COL = "Дата операции"


def load_dataframe() -> pd.DataFrame:
    """Читает транзакции и возвращает их в виде датафрейма."""
    return pd.DataFrame(get_transactions())


def month_bounds(date_str: str) -> tuple:
    """Возвращает (начало месяца, конец месяца) по строке с датой."""
    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
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
        info = totals.setdefault(
            item["recipient"], {"total": 0.0, "count": 0}
        )
        info["total"] += item["amount"]
        info["count"] += 1
    ranked = sorted(
        totals.items(), key=lambda kv: kv[1]["total"], reverse=True
    )
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
    if command == "main":
        return main_page(args.date)

    if command == "events":
        return events_page(args.date, period=args.period)

    if command == "cashback":
        try:
            month_number = int(args.month)
        except ValueError:
            raise ValueError(
                "--month для cashback должен быть номером месяца,"
                " например 7"
            )
        return cashback_categories(get_transactions(), args.year,
                                   month_number)

    if command == "invest":
        transactions = []
        for record in get_transactions():
            dt = pd.to_datetime(record[DATE_COL]).strftime("%Y-%m-%d")
            amount = record.get(
                "Сумма операции", record.get("Сумма в валюте счёта", 0)
            )
            transactions.append({"Дата операции": dt,
                                 "Сумма операции": amount})
        return investment_bank(args.month, transactions, args.limit)

    if command == "transfers":
        if args.date:
            start, end = month_bounds(args.date)
            return transfers_to_individuals(get_transactions(), start, end)
        return transfers_to_individuals(get_transactions())

    if command == "recipients":
        start, end = month_bounds(args.date)
        filtered = transfers_to_individuals(get_transactions(), start, end)
        return top_recipients_json(json.loads(filtered))

    if command == "search":
        return search_transactions(args.query, get_transactions())

    if command == "phones":
        return phone_number_search(get_transactions())

    df = load_dataframe()
    if command == "category":
        return spending_by_category(df, args.category,
                                    args.date).to_string(index=False)
    if command == "weekday":
        return spending_by_weekday(df, args.date).to_string(index=False)
    if command == "workday":
        return spending_by_workday(df, args.date).to_string(index=False)
    raise ValueError(f"Неизвестная команда: {command}")


def parse_args() -> argparse.Namespace:
    """Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Веб-приложение «Анализ транзакций»"
    )
    parser.add_argument(
        "command",
        choices=["main", "events", "cashback", "invest", "transfers",
                 "recipients", "search", "phones", "category",
                 "weekday", "workday"],
    )
    parser.add_argument("date_pos", nargs="?", default=None,
                        help="Дата позицией: YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--date", dest="date_opt", default=None,
                        help="Дата опцией: YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--period", default="M",
                        help="Диапазон для events: W, M, Y или ALL")
    parser.add_argument("--category", help="Категория для отчёта")
    parser.add_argument("--query", help="Строка поиска для команды search")
    parser.add_argument("--year", type=int, help="Год для сервиса кешбэка")
    parser.add_argument(
        "--month",
        help="Месяц: номер для cashback, YYYY-MM для invest",
    )
    parser.add_argument("--limit", type=int, default=50,
                        help="Порог округления Инвесткопилки: 10, 50 или 100")
    args = parser.parse_args()

    args.date = args.date_opt or args.date_pos
    if args.command == "search" and args.date_pos and not args.query:
        args.query = args.date_pos  # допускаем: search "Лента"
    if command_needs_date(args.command) and not args.date:
        parser.error(f"для команды {args.command} укажите дату")
    if args.command == "cashback" and (not args.year or not args.month):
        parser.error("для команды cashback укажите --year и --month")
    if args.command == "invest" and not args.month:
        parser.error("для команды invest укажите --month в формате YYYY-MM")
    if args.command == "category" and not args.category:
        parser.error("для команды category укажите --category")
    if args.command == "search" and not args.query:
        parser.error("для команды search укажите --query")
    return args


def command_needs_date(command: str) -> bool:
    """Команды, которым обязательна дата."""
    return command in ("main", "events", "recipients", "category",
                       "weekday", "workday")


def main() -> None:
    args = parse_args()
    try:
        result = run(args.command, args)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    print(result)


if __name__ == "__main__":
    main()
