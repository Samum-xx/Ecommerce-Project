"""Тесты для модуля src.reports (страница «Отчёты»)."""
from datetime import datetime

import pandas as pd
import pytest

from src.reports import (spending_by_category, spending_by_weekday,
                         spending_by_workday)


@pytest.fixture
def transactions() -> pd.DataFrame:
    """Транзакции за три месяца: июнь, июль, август 2024."""
    return pd.DataFrame([
        # Май — вне окна
        {"Дата операции": datetime(2024, 5, 20, 10, 0),
         "Сумма в валюте счёта": -5000.0,
         "Категория по-умолчанию": "Супермаркеты"},
        # Июнь
        {"Дата операции": datetime(2024, 6, 5, 10, 0),
         "Сумма в валюте счёта": -1000.0,
         "Категория по-умолчанию": "Супермаркеты"},
        {"Дата операции": datetime(2024, 6, 15, 12, 0),
         "Сумма в валюте счёта": -2000.0,
         "Категория по-умолчанию": "Супермаркеты"},
        {"Дата операции": datetime(2024, 6, 20, 14, 0),
         "Сумма в валюте счёта": -800.0,
         "Категория по-умолчанию": "Транспорт"},
        # Июль
        {"Дата операции": datetime(2024, 7, 3, 9, 0),
         "Сумма в валюте счёта": -3000.0,
         "Категория по-умолчанию": "Супермаркеты"},
        {"Дата операции": datetime(2024, 7, 10, 11, 0),
         "Сумма в валюте счёта": 5000.0,
         "Категория по-умолчанию": "Супермаркеты"},
        {"Дата операции": datetime(2024, 7, 12, 13, 0),
         "Сумма в валюте счёта": -1200.0,
         "Категория по-умолчанию": "Транспорт"},
        # Август
        {"Дата операции": datetime(2024, 8, 1, 10, 0),
         "Сумма в валюте счёта": -2500.0,
         "Категория по-умолчанию": "Супермаркеты"},
        {"Дата операции": datetime(2024, 8, 14, 10, 0),
         "Сумма в валюте счёта": -500.0,
         "Категория по-умолчанию": "Супермаркеты"},
        {"Дата операции": datetime(2024, 8, 20, 10, 0),
         "Сумма в валюте счёта": -9000.0,
         "Категория по-умолчанию": "Супермаркеты"},
    ])


class TestSpendingByCategory:
    def test_monthly_sums(self, transactions):
        result = spending_by_category(
            transactions, "Супермаркеты", "2024-08-15 18:00:00")
        by_month = dict(zip(result["month"], result["spent"]))
        assert by_month["2024-06"] == 3000.0
        assert by_month["2024-07"] == 3000.0  # пополнение не учтено
        assert by_month["2024-08"] == 3000.0  # 2500 + 500, без 20.08

    def test_window_excludes_may(self, transactions):
        result = spending_by_category(
            transactions, "Супермаркеты", "2024-08-15 18:00:00")
        assert "2024-05" not in result["month"].tolist()

    def test_unknown_category(self, transactions):
        result = spending_by_category(
            transactions, "Космос", "2024-08-15 18:00:00")
        assert result.empty

    def test_returns_dataframe(self, transactions):
        result = spending_by_category(
            transactions, "Транспорт", "2024-08-15 18:00:00")
        assert isinstance(result, pd.DataFrame)

    def test_older_date(self, transactions):
        result = spending_by_category(
            transactions, "Транспорт", "2024-05-15 18:00:00")
        assert result.empty

    def test_default_date_is_now(self, transactions):
        """Без даты берётся текущая; данные 2024 года вне окна."""
        result = spending_by_category(transactions, "Супермаркеты")
        assert result.empty


class TestSpendingByWeekday:
    def test_average_per_weekday(self, transactions):
        result = spending_by_weekday(transactions, "2024-08-15 18:00:00")
        by_day = dict(zip(result["weekday"], result["average_spent"]))
        # Среда: 05.06 (1000), 03.07 (3000), 14.08 (500) -> среднее 1500
        assert by_day["Среда"] == 1500.0
        # Суббота: только 15.06 (2000)
        assert by_day["Суббота"] == 2000.0
        # Четверг: 20.06 (800), 01.08 (2500) -> 1650
        assert by_day["Четверг"] == 1650.0

    def test_all_weekdays_present(self, transactions):
        result = spending_by_weekday(transactions, "2024-08-15 18:00:00")
        assert len(result) == 7  # семь дней недели, даже без трат

    def test_empty_window(self, transactions):
        result = spending_by_weekday(transactions, "2024-05-15 18:00:00")
        assert result.empty


class TestSpendingByWorkday:
    def test_two_day_types(self, transactions):
        result = spending_by_workday(transactions, "2024-08-15 18:00:00")
        by_type = dict(zip(result["day_type"], result["average_spent"]))
        assert set(by_type) <= {"Рабочий", "Выходной"}

    def test_values(self, transactions):
        result = spending_by_workday(transactions, "2024-08-15 18:00:00")
        by_type = dict(zip(result["day_type"], result["average_spent"]))
        expenses = [1000, 2000, 800, 3000, 1200, 2500, 500]
        weekdays = [w.weekday() for w in [
            datetime(2024, 6, 5), datetime(2024, 6, 15), datetime(2024, 6, 20),
            datetime(2024, 7, 3), datetime(2024, 7, 12),
            datetime(2024, 8, 1), datetime(2024, 8, 14),
        ]]
        expected_work = round(
            sum(v for v, w in zip(expenses, weekdays) if w < 5)
            / sum(1 for w in weekdays if w < 5), 2)
        expected_weekend = round(
            sum(v for v, w in zip(expenses, weekdays) if w >= 5)
            / sum(1 for w in weekdays if w >= 5), 2)
        assert by_type["Рабочий"] == expected_work
        assert by_type["Выходной"] == expected_weekend

    def test_empty_window(self, transactions):
        result = spending_by_workday(transactions, "2024-05-15 18:00:00")
        assert result.empty
