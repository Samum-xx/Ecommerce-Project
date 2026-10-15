# main.py
import json
from pathlib import Path
from src.shop import Category, Product


def load_data_from_json(file_path: str):
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    categories = []
    for cat_data in data.get("categories", []):
        products = []
        for prod_data in cat_data.get("products", []):
            p = Product(
                name=prod_data["name"],
                description=prod_data["description"],
                price=prod_data["price"],
                quantity=prod_data["quantity"]
            )
            products.append(p)

        c = Category(
            name=cat_data["name"],
            description=cat_data["description"],
            products=products
        )
        categories.append(c)
    return categories


print("✅ Создаём тестовые объекты вручную...")
p1 = Product("Чайник", "Электрический чайник", 3500.0, 20)
c1 = Category("Кухня", "Товары для кухни", [p1])
print(f"   Категория: {c1.name}, товаров: {len(c1.products)}")
print(f"   Итого: категорий={Category.category_count}, товаров={Category.product_count}")

print("\n✅ Загружаем данные из products.json...")
cats = load_data_from_json("products.json")
for c in cats:
    print(f"   - {c.name}: {len(c.products)} товаров")

print(f"\n✅ Финальные счётчики: категорий={Category.category_count}, товаров={Category.product_count}")
