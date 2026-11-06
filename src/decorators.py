"""Декоратор для функций-отчётов: сохраняет результат в файл."""
import functools
import json
import os
from typing import Any, Callable

import pandas as pd

DEFAULT_REPORT_PATH = os.path.join("reports", "report_output.json")


def save_report_to_file(filename: str | None = None) -> Callable:
    """Декоратор записи результата функции-отчёта в файл.

    Без параметра — пишет в файл по умолчанию,
    с параметром — в указанный файл.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            path = filename or DEFAULT_REPORT_PATH
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                if isinstance(result, str):
                    f.write(result)
                elif isinstance(result, pd.DataFrame):
                    f.write(result.to_json(
                        orient="records", force_ascii=False, indent=2
                    ))
                else:
                    f.write(json.dumps(result, ensure_ascii=False, indent=2))
            return result

        return wrapper

    return decorator
