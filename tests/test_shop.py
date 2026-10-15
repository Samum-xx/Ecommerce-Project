from src.shop import Product, Category


def test_product_initialization():
    p = Product("Ноутбук", "Мощный ноутбук", 79999.99, 10)
    assert p.name == "Ноутбук"
    assert p.description == "Мощный ноутбук"
    assert p.price == 79999.99
    assert p.quantity == 10


def test_category_initialization_empty():
    # Сбрасываем счётчики
    Category.category_count = 0
    Category.product_count = 0

    c = Category("Электроника", "Все электронные товары")
    assert c.name == "Электроника"
    assert len(c.products) == 0
    assert Category.category_count == 1
    assert Category.product_count == 0


def test_category_with_products():
    # Сбрасываем счётчики
    Category.category_count = 0
    Category.product_count = 0

    p1 = Product("Мышь", "Беспроводная мышь", 1500.0, 50)
    p2 = Product("Клавиатура", "Механическая клавиатура", 4000.0, 30)
    c = Category("Аксессуары", "Мышки и клавиатуры", [p1, p2])

    assert len(c.products) == 2
    assert Category.category_count == 1
    assert Category.product_count == 2


def test_multiple_categories_counters():
    # Сбрасываем счётчики
    Category.category_count = 0
    Category.product_count = 0

    c1 = Category("Одежда", "Футболки")
    c2 = Category("Обувь", "Кроссовки")

    assert Category.category_count == 2
    assert Category.product_count == 0

    p = Product("Кеды", "Синие кеды", 5000.0, 20)
    c3 = Category("Спорт", "Инвентарь", [p])

    assert Category.category_count == 3
    assert Category.product_count == 1
