"""Тесты для модуля src.services (страница «Сервисы»)."""
import json
from datetime import datetime

import pytest

from src.services import (cashback_categories, investment_bank,
                          phone_number_search, search_transactions,
                          transfers_to_individuals)


@pytest.fixture
def transactions() -> list:
    """Транзакции за несколько месяцев."""
    return [
        {"Дата операции": datetime(2024, 6, 5, 10, 0),
         "Сумма в валюте счёта": -5000.0,
         "Категория по-умолчанию": "Супермаркеты",
         "Описание": "Лента"},
        {"Дата операции": datetime(2024, 6, 10, 10, 0),
         "Сумма в валюте счёта": -1000.0,
         "Категория по-умолчанию": "Транспорт",
         "Описание": "Метро"},
        {"Дата операции": datetime(2024, 7, 1, 10, 0),
         "Сумма в валюте счёта": -4000.0,
         "Категория по-умолчанию": "Переводы",
         "Описание": "Илья К."},
        {"Дата операции": datetime(2024, 7, 2, 11, 0),
         "Сумма в валюте счёта": -22000.0,
         "Категория по-умолчанию": "Переводы",
         "Описание": "Мария Х."},
        {"Дата операции": datetime(2024, 7, 3, 12, 0),
         "Сумма в валюте счёта": -8800.0,
         "Категория по-умолчанию": "Переводы",
         "Описание": "Между своими счетами"},
        {"Дата операции": datetime(2024, 7, 4, 13, 0),
         "Сумма в валюте счёта": -1000.0,
         "Категория по-умолчанию": "Переводы",
         "Описание": "Налоги"},
        {"Дата операции": datetime(2024, 7, 5, 14, 0),
         "Сумма в валюте счёта": 5000.0,
         "Категория по-умолчанию": "Переводы",
         "Описание": "Пополнение"},
        {"Дата операции": datetime(2024, 7, 6, 15, 0),
         "Сумма в валюте счёта": -500.0,
         "Категория по-умолчанию": "Супермаркеты",
         "Описание": "Пятёрочка"},
        {"Дата операции": datetime(2023, 7, 1, 10, 0),
         "Сумма в валюте счёта": -999.0,
         "Категория по-умолчанию": "Транспорт",
         "Описание": "Прошлый год"},
    ]


# ------------------- cashback_categories -------------------

class TestCashbackCategories:
    def test_dict_per_category_for_month(self, transactions):
        result = json.loads(cashback_categories(transactions, 2024, 7))
        assert result["Переводы"] == 358.0  # (4000+22000+8800+1000)/100
        assert result["Супермаркеты"] == 5.0

    def test_only_requested_month(self, transactions):
        result = json.loads(cashback_categories(transactions, 2024, 6))
        assert result["Супермаркеты"] == 50.0
        assert "Транспорт" in result
        assert "Переводы" not in result

    def test_income_excluded(self, transactions):
        result = json.loads(cashback_categories(transactions, 2024, 7))
        # пополнение 5000 не даёт кешбэк
        assert result["Переводы"] == 358.0

    def test_other_year_excluded(self, transactions):
        result = json.loads(cashback_categories(transactions, 2023, 7))
        assert result["Транспорт"] == 9.99

    def test_empty_data(self):
        assert json.loads(cashback_categories([], 2024, 7)) == {}

    def test_no_transactions_in_month(self, transactions):
        assert json.loads(cashback_categories(transactions, 2024, 1)) == {}


# ------------------- investment_bank -------------------

class TestInvestmentBank:
    def _tx(self, day: int, amount: float) -> dict:
        return {"Дата операции": f"2024-07-{day:02d}",
                "Сумма операции": amount}

    def test_rounding_to_limit(self):
        txs = [self._tx(10, -1712.0)]
        assert investment_bank("2024-07", txs, 50) == 38.0

    def test_multiple_transactions(self):
        txs = [
            self._tx(10, -1712.0),
            self._tx(20, -99.0),
            self._tx(25, -110.0),
        ]
        # 1712->1750 (+38), 99->100 (+1), 110->150 (+40)
        assert investment_bank("2024-07", txs, 50) == 79.0

    def test_exact_multiple_no_savings(self):
        txs = [self._tx(10, -100.0)]
        assert investment_bank("2024-07", txs, 50) == 0.0

    def test_income_not_saved(self):
        txs = [self._tx(10, 5000.0)]
        assert investment_bank("2024-07", txs, 100) == 0.0

    def test_other_month_excluded(self):
        txs = [
            self._tx(10, -1712.0),
            {"Дата операции": "2024-06-15",
             "Сумма операции": -1712.0},
        ]
        assert investment_bank("2024-07", txs, 50) == 38.0

    def test_empty_transactions(self):
        assert investment_bank("2024-07", [], 50) == 0.0

    def test_returns_float(self):
        assert isinstance(investment_bank("2024-07", [], 50), float)


# ------------------- transfers_to_individuals -------------------

class TestTransfersToIndividuals:
    def test_only_person_pattern(self, transactions):
        data = json.loads(transfers_to_individuals(transactions))
        recipients = [item["recipient"] for item in data]
        assert set(recipients) == {"Илья К.", "Мария Х."}

    def test_excludes_system_descriptions(self, transactions):
        data = json.loads(transfers_to_individuals(transactions))
        found = [item["recipient"] for item in data]
        assert "Налоги" not in found
        assert "Между своими счетами" not in found

    def test_only_expenses(self, transactions):
        data = json.loads(transfers_to_individuals(transactions))
        assert all(item["amount"] > 0 for item in data)

    def test_positive_amounts(self, transactions):
        data = json.loads(transfers_to_individuals(transactions))
        amounts = {item["recipient"]: item["amount"] for item in data}
        assert amounts["Илья К."] == 4000.0
        assert amounts["Мария Х."] == 22000.0

    def test_period_filter(self, transactions):
        start = datetime(2024, 7, 1, 0, 0)
        end = datetime(2024, 7, 31, 23, 59)
        data = json.loads(transfers_to_individuals(transactions, start, end))
        assert len(data) == 2

    def test_empty_data(self):
        assert json.loads(transfers_to_individuals([])) == []


# ------------------- search / phones -------------------

class TestSearchTransactions:
    def test_case_insensitive(self, transactions):
        data = json.loads(search_transactions("лента", transactions))
        assert any(item["description"] == "Лента" for item in data)

    def test_by_category(self, transactions):
        data = json.loads(search_transactions("транспорт", transactions))
        assert all(item["category"] == "Транспорт" for item in data)

    def test_no_results(self, transactions):
        assert json.loads(search_transactions("космос", transactions)) == []

    def test_empty_data(self):
        assert search_transactions("лента", []) == "[]"


class TestPhoneNumberSearch:
    def _row(self, day: int, amount: float, description: str) -> dict:
        return {"Дата операции": datetime(2024, 7, day),
                "Сумма в валюте счёта": amount,
                "Категория по-умолчанию": "Связь",
                "Описание": description}

    def test_both_formats(self):
        data = [
            self._row(1, -100.0, "Я МТС +7 921 11-22-33"),
            self._row(2, -200.0, "Тинькофф Мобайл +7 (995) 555-55-55"),
            self._row(3, -300.0, "МТС Mobile 89000000000"),
            self._row(4, -400.0, "Лента"),
            self._row(5, -500.0, "Счёт 12345678"),
        ]
        found = json.loads(phone_number_search(data))
        assert len(found) == 3
        assert all("Лента" != item["description"] for item in found)

    def test_empty_data(self):
        assert phone_number_search([]) == "[]"
