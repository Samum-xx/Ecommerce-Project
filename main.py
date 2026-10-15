import json
from pathlib import Path
from src.shop import Category, Product


def load_data_from_json(file_path: str):
    """Загружает данные из JSON и возвращает список объектов Category."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path.absolute()}")

    try:
        with path.open(mode="r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка формата JSON: {e}")

    categories = []

    for cat_data in data.get("categories", ):
        products = []
        for prod_data in cat_data.get("products", ):
            p = Product(
                name=prod_data.get("name", "Без названия"),
                description=prod_data.get("description", ""),
                price=prod_data.get("price", 0.0),
                quantity=prod_data.get("quantity", 0)
            )
            products.append(p)

        c = Category(
            name=cat_data.get("name", "Без названия"),
            description=cat_data.get("description", ""),
            products=products
        )
        categories.append(c)

    return categories


def main():
    print("✅ Создаём тестовые объекты вручную...")
    p1 = Product("Чайник", "Электрический чайник", 3500.0, 20)
    c1 = Category("Кухня", "Товары для кухни", [p1])

    print(f"   Категория: {c1.name}, товаров: {len(c1.products)}")
    print(f"   Итого: категорий={Category.category_count}, товаров={Category.product_count}")

    print("\n✅ Загружаем данные из products.json...")

    script_dir = Path(__file__).parent
    json_path = script_dir / "products.json"

    try:
        cats = load_data_from_json(json_path)
        for c in cats:
            print(f"   - {c.name}: {len(c.products)} товаров")

        print(f"\n✅ Финальные счётчики: категорий={Category.category_count}, товаров={Category.product_count}")
    except FileNotFoundError as e:
        print(f"❌ Ошибка: {e}")
    except ValueError as e:
        print(f"❌ Ошибка данных: {e}")


if __name__ == "__main__":
    main()
