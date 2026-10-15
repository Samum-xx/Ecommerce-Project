from typing import List, Optional


class Product:
    def __init__(
        self,
        name: str,
        description: str,
        price: float,
        quantity: int,
    ) -> None:
        self.name = name
        self.description = description
        self.price = price
        self.quantity = quantity


class Category:
    category_count = 0
    product_count = 0

    def __init__(
        self,
        name: str,
        description: str,
        products: Optional[List[Product]] = None,
    ) -> None:
        self.name = name
        self.description = description

        if products is not None:
            self.products: List[Product] = products
        else:
            self.products: List[Product] = []

        Category.category_count += 1
        Category.product_count += len(self.products)

    def add_product(self, product: Product) -> None:
        self.products.append(product)
        Category.product_count += 1
