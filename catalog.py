import json


def load_products(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_categories(products):
    cats = []
    for p in products:
        value = p.get("category", "")
        if value and value not in cats:
            cats.append(value)
    return cats


def get_products_by_category(products, category: str):
    return [p for p in products if p.get("category") == category or p.get("subcategory") == category]


def get_product_by_id(products, product_id: int):
    return next((p for p in products if p.get("id") == product_id), None)


def format_price(price: int):
    return f"{price:,}".replace(",", " ")