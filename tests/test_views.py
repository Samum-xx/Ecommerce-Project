"""Тесты для модуля src.views (страница «Главная»)."""
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from src.views import (
    cards_stats,
    filter_by_period,
    get_currency_rates,
    get_stock_prices,
    main_page,
    top_transactions,
)


@pytest.fixture
def transactions() -> list:
    """Несколько тестовых транзакций за июль 2024."""
    return [
        {"Номер карты": "*2721",
         "Дата операции": datetime(2024, 7, 1, 10, 0),
         "Сумма в валюте счёта": -1000.0,
         "Категория по-умолчанию": "Супермаркеты",
         "Описание": "Пятёрочка"},
        {"Номер карты": "*2721",
         "Дата операции": datetime(2024, 7, 5, 12, 0),
         "Сумма в валюте счёта": -2000.0,
         "Категория по-умолчанию": "Переводы",
         "Описание": "Перевод между счетами"},
        {"Номер карты": "*3661",
         "Дата операции": datetime(2024, 7, 10, 15, 0),
         "Сумма в валюте счёта": 5000.0,
         "Категория по-умолчанию": "Переводы",
         "Описание": "Пополнение"},
        {"Номер карты": "*3661",
         "Дата операции": datetime(2024, 6, 20, 15, 0),
         "Сумма в валюте счёта": -999.0,
         "Категория по-умолчанию": "ЖКХ",
         "Описание": "Июньская транзакция"},
        {"Номер карты": "*4156",
         "Дата операции": datetime(2024, 7, 15, 20, 0),
         "Сумма в валюте счёта": -300.0,
         "Категория по-умолчанию": "Транспорт",
         "Описание": "Метро"},
    ]


class TestFilterByPeriod:
    def test_keeps_only_current_month(self, transactions):
        df = pd.DataFrame(transactions)
        result = filter_by_period(df, datetime(2024, 7, 30, 18, 0))
        # июньская транзакция должна исчезнуть
        assert len(result) == 4

    def test_empty_df(self):
        df = pd.DataFrame(columns=["Дата операции"])
        result = filter_by_period(df, datetime(2024, 7, 30))
        assert len(result) == 0


class TestCardsStats:
    def test_only_expenses_counted(self, transactions):
        dt = datetime(2024, 7, 30, 18, 0)
        stats = cards_stats(transactions, dt)
        by_card = {item["last_digits"]: item for item in stats}
        # 2721: расходы 1000 + 2000 = 3000, кешбэк 30
        assert by_card["2721"]["total_spent"] == 3000.0
        assert by_card["2721"]["cashback"] == 30.0
        # 3661: в июле только пополнение — карты быть не должно
        assert "3661" not in by_card
        # 4156: один расход 300, кешбэк 3
        assert by_card["4156"]["total_spent"] == 300.0
        assert by_card["4156"]["cashback"] == 3.0

    def test_no_expenses(self):
        df = [{"Номер карты": "*1111",
               "Дата операции": datetime(2024, 7, 1),
               "Сумма в валюте счёта": 100.0,
               "Категория по-умолчанию": "X",
               "Описание": "Y"}]
        assert cards_stats(df, datetime(2024, 7, 2)) == []


class TestTopTransactions:
    def test_top5_sorted_by_amount(self, transactions):
        dt = datetime(2024, 7, 30, 18, 0)
        top = top_transactions(transactions, dt)
        amounts = [item["amount"] for item in top]
        assert amounts == sorted(amounts, reverse=True)
        assert amounts[0] == max(amounts)

    def test_june_excluded(self, transactions):
        dt = datetime(2024, 7, 30, 18, 0)
        top = top_transactions(transactions, dt)
        assert all(item["date"] != "20.06.2024" for item in top)

    def test_date_format(self, transactions):
        dt = datetime(2024, 7, 30, 18, 0)
        top = top_transactions(transactions, dt)
        assert top[0]["date"] == "10.07.2024"


class TestGetCurrencyRates:
    @patch("src.views.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"rates": {"RUB": 100.0, "USD": 1.0, "EUR": 1.25}},
        )
        mock_get.return_value.raise_for_status = lambda: None
        result = get_currency_rates(["USD", "EUR"])
        assert result == [
            {"currency": "USD", "rate": 100.0},
            {"currency": "EUR", "rate": 80.0},
        ]

    @patch("src.views.requests.get")
    def test_api_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "network down")
        assert get_currency_rates(["USD"]) == []


class TestGetStockPrices:
    @patch("src.views.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "chart": {"result": [{"meta": {"regularMarketPrice": 123.45}}]}
            },
        )
        mock_get.return_value.raise_for_status = lambda: None
        result = get_stock_prices(["AAPL"])
        assert result == [{"stock": "AAPL", "price": 123.45}]

    @patch("src.views.requests.get")
    def test_api_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "network down")
        assert get_stock_prices(["AAPL"]) == []


class TestMainPage:
    @patch("src.views.get_stock_prices", return_value=[])
    @patch("src.views.get_currency_rates", return_value=[])
    @patch(
        "src.views.get_user_settings",
        return_value={"user_currencies": [], "user_stocks": []},
    )
    @patch("src.views.get_transactions")
    def test_main_page_structure(
        self, mock_tx, mock_settings, mock_rates, mock_stocks, transactions
    ):
        mock_tx.return_value = transactions
        result = json.loads(main_page("2024-07-30 18:00:00"))
        assert result["greeting"] == "Добрый вечер"
        assert isinstance(result["cards"], list)
        assert isinstance(result["top_transactions"], list)
        assert result["currency_rates"] == []
        assert result["stock_prices"] == []
