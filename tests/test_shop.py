# tests/test_shop.py
from src.shop import Product, Category

def test_product_initialization():
    p = Product("Ноутбук", "Мощный ноутбук", 79999.99, 10)
    assert p.name == "Ноутбук"
    assert p.description == "Мощный ноутбук"
    assert p.price == 79999.99
    assert p.quantity == 10

def test_category_initialization_empty():
    c = Category("Электроника", "Все электронные товары")
    assert c.name == "Электроника"
    assert len(c.products) == 0
    assert Category.category_count == 1
    assert Category.product_count == 0

def test_category_with_products():
    p1 = Product("Мышь", "Беспроводная мышь", 1500.0, 50)
    p2 = Product("Клавиатура", "Механическая клавиатура", 4000.0, 30)
    c = Category("Аксессуары", "Мышки и клавиатуры", [p1, p2])
    assert len(c.products) == 2
    assert Category.category_count == 1
    assert Category.product_count == 2

def test_add_product_updates_count():
    c = Category("Одежда", "Футболки и джинсы")
    initial_count = Category.product_count
    p = Product("Футболка", "Хлопковая футболка", 1200.0, 100)
    c.add_product(p)
    assert len(c.products) == 1
    assert Category.product_count == initial_count + 1
