import functools
import json
from datetime import datetime


def report_to_json(func):
    """Декоратор: после каждого вызова функции пишет отчёт в JSON-файл."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        report = {
            "функция": func.__name__,
            "аргументы": {"args": args, "kwargs": kwargs},
            "результат": result,
            "время вызова": datetime.now().isoformat(),
        }
        with open("report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return result
    return wrapper


@report_to_json
def get_report():
    return {"статус": "ok", "товаров": 5}
