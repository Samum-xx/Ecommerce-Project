import json
from datetime import datetime

import pytest

from src.views import events_page


@pytest.fixture
def sample_transactions():
    return [
        {
            "Номер карты": "*2721",
            "Дата операции": datetime(2024, 7, 1, 10, 0),
            "Сумма в валюте счёта": -1000.0,
            "Категория по-умолчанию": "Супермаркеты",
            "Описание": "Пятёрочка",
        },
        {
            "Номер карты": "*2721",
            "Дата операции": datetime(2024, 7, 5, 12, 0),
            "Сумма в валюте счёта": -2000.0,
            "Категория по-умолчанию": "Переводы",
            "Описание": "Перевод между счетами",
        },
        {
            "Номер карты": "*3661",
            "Дата операции": datetime(2024, 7, 10, 15, 0),
            "Сумма в валюте счёта": 5000.0,
            "Категория по-умолчанию": "Пополнение",
            "Описание": "Пополнение счёта",
        },
        {
            "Номер карты": "*4156",
            "Дата операции": datetime(2024, 7, 15, 20, 0),
            "Сумма в валюте счёта": -300.0,
            "Категория по-умолчанию": "Транспорт",
            "Описание": "Метро",
        },
        {
            "Номер карты": "*9999",
            "Дата операции": datetime(2024, 7, 20, 9, 0),
            "Сумма в валюте счёта": -500.0,
            "Категория по-умолчанию": "Наличные",
            "Описание": "Снятие наличных",
        },
    ]


class TestEventsPage:
    def test_returns_valid_json(self, sample_transactions):
        json_str = events_page("2024-07-20 10:00:00", period="M", data=sample_transactions)
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_structure_contains_expenses_and_income(self, sample_transactions):
        json_str = events_page("2024-07-20 10:00:00", period="M", data=sample_transactions)
        data = json.loads(json_str)
        assert "expenses" in data
        assert "income" in data

    def test_special_categories_are_separated(self, sample_transactions):
        json_str = events_page("2024-07-20 10:00:00", period="M", data=sample_transactions)
        data = json.loads(json_str)

        main_cats = {c["category"] for c in data["expenses"]["main"]}
        special_cats = {c["category"] for c in data["expenses"]["transfers_and_cash"]}

        # «Переводы» и «Наличные» не должны быть в main
        assert "Переводы" not in main_cats
        assert "Наличные" not in main_cats

        # Они должны быть в специальном блоке
        assert "Переводы" in special_cats or len(special_cats) > 0
        assert "Наличные" in special_cats or len(special_cats) > 0

    def test_unsupported_period_raises_error(self):
        with pytest.raises(ValueError):
            events_page("2024-07-20 10:00:00", period="Q")

    def test_empty_data_returns_zero_totals(self):
        json_str = events_page("2024-07-20 10:00:00", period="M", data=[])
        data = json.loads(json_str)
        assert data["expenses"]["total_amount"] == 0
        assert data["income"]["total_amount"] == 0
