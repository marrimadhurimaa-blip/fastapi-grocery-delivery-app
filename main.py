from fastapi import FastAPI, Query, status
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# -------------------- DATA --------------------

products = [
    {"id": 1, "name": "Milk", "price": 50, "category": "Dairy", "is_available": True},
    {"id": 2, "name": "Bread", "price": 30, "category": "Bakery", "is_available": True},
    {"id": 3, "name": "Rice", "price": 80, "category": "Grains", "is_available": True},
    {"id": 4, "name": "Eggs", "price": 60, "category": "Dairy", "is_available": False},
    {"id": 5, "name": "Apple", "price": 40, "category": "Fruits", "is_available": True},
]

orders = []
order_counter = 1
cart = []

# -------------------- HOME --------------------

@app.get("/")
def home():
    return {"message": "Welcome to Grocery Delivery App"}

# -------------------- GET PRODUCTS --------------------

@app.get("/products")
def get_products():
    return {"data": products, "total": len(products)}

@app.get("/products/summary")
def summary():
    available = len([p for p in products if p["is_available"]])
    unavailable = len(products) - available
    categories = list(set([p["category"] for p in products]))
    return {
        "total": len(products),
        "available": available,
        "unavailable": unavailable,
        "categories": categories
    }

@app.get("/products/{product_id}")
def get_product(product_id: int):
    for p in products:
        if p["id"] == product_id:
            return p
    return {"error": "Product not found"}

# -------------------- PYDANTIC MODELS --------------------

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=10)
    address: str = Field(..., min_length=5)
    order_type: str = "delivery"

class NewProduct(BaseModel):
    name: str
    price: int = Field(..., gt=0)
    category: str

class CheckoutRequest(BaseModel):
    customer_name: str
    address: str

# -------------------- HELPERS --------------------

def find_product(product_id):
    for item in products:
        if item["id"] == product_id:
            return item
    return None

def calculate_total(price, quantity, order_type="delivery"):
    total = price * quantity
    if order_type == "delivery":
        total += 20
    return total

# -------------------- CREATE ORDER --------------------

@app.post("/orders")
def create_order(order: OrderRequest):
    global order_counter

    product = find_product(order.product_id)

    if not product:
        return {"error": "Product not found"}

    if not product["is_available"]:
        return {"error": "Product not available"}

    total = calculate_total(product["price"], order.quantity, order.order_type)

    new_order = {
        "order_id": order_counter,
        "customer_name": order.customer_name,
        "product": product["name"],
        "quantity": order.quantity,
        "total_price": total
    }

    orders.append(new_order)
    order_counter += 1

    return new_order

@app.get("/orders")
def get_orders():
    return {"orders": orders, "total": len(orders)}

# -------------------- CRUD --------------------

@app.post("/products", status_code=201)
def add_product(item: NewProduct):
    for p in products:
        if p["name"].lower() == item.name.lower():
            return {"error": "Duplicate product"}

    new = {
        "id": len(products) + 1,
        "name": item.name,
        "price": item.price,
        "category": item.category,
        "is_available": True
    }
    products.append(new)
    return new

@app.put("/products/{product_id}")
def update_product(product_id: int, price: Optional[int] = None, is_available: Optional[bool] = None):
    product = find_product(product_id)

    if not product:
        return {"error": "Not found"}

    if price is not None:
        product["price"] = price

    if is_available is not None:
        product["is_available"] = is_available

    return product

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    product = find_product(product_id)

    if not product:
        return {"error": "Not found"}

    products.remove(product)
    return {"message": "Deleted"}

# -------------------- CART --------------------

@app.post("/cart/add")
def add_to_cart(product_id: int, quantity: int = 1):
    product = find_product(product_id)

    if not product:
        return {"error": "Not found"}

    if not product["is_available"]:
        return {"error": "Not available"}

    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            return {"message": "Updated quantity"}

    cart.append({
        "product_id": product_id,
        "name": product["name"],
        "price": product["price"],
        "quantity": quantity
    })

    return {"message": "Added to cart"}

@app.get("/cart")
def view_cart():
    total = sum(item["price"] * item["quantity"] for item in cart)
    return {"cart": cart, "total": total}

@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):
    for item in cart:
        if item["product_id"] == product_id:
            cart.remove(item)
            return {"message": "Removed"}
    return {"error": "Not found"}

@app.post("/cart/checkout", status_code=201)
def checkout(data: CheckoutRequest):
    global order_counter

    if not cart:
        return {"error": "Cart is empty"}

    placed_orders = []
    total_amount = 0

    for item in cart:
        total = item["price"] * item["quantity"]
        total_amount += total

        new_order = {
            "order_id": order_counter,
            "customer_name": data.customer_name,
            "product": item["name"],
            "quantity": item["quantity"],
            "total_price": total
        }

        orders.append(new_order)
        placed_orders.append(new_order)
        order_counter += 1

    cart.clear()

    return {"orders": placed_orders, "grand_total": total_amount}

# -------------------- FILTER --------------------

@app.get("/products/filter")
def filter_products(
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    is_available: Optional[bool] = None
):
    result = products

    if category is not None:
        result = [p for p in result if p["category"].lower() == category.lower()]

    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    if is_available is not None:
        result = [p for p in result if p["is_available"] == is_available]

    return {"data": result, "count": len(result)}

# -------------------- SEARCH --------------------

@app.get("/products/search")
def search(keyword: str):
    result = [
        p for p in products
        if keyword.lower() in p["name"].lower()
        or keyword.lower() in p["category"].lower()
    ]

    if not result:
        return {"message": "No results found"}

    return {"results": result, "total_found": len(result)}

# -------------------- SORT --------------------

@app.get("/products/sort")
def sort_products(sort_by: str = "price", order: str = "asc"):
    if sort_by not in ["price", "name", "category"]:
        return {"error": "Invalid sort field"}

    reverse = True if order == "desc" else False

    sorted_data = sorted(products, key=lambda x: x[sort_by], reverse=reverse)

    return {"sorted": sorted_data}

# -------------------- PAGINATION --------------------

@app.get("/products/page")
def paginate(page: int = Query(1, ge=1), limit: int = Query(3, ge=1, le=10)):
    start = (page - 1) * limit
    total = len(products)

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
        "data": products[start:start + limit]
    }

# -------------------- COMBINED --------------------

@app.get("/products/browse")
def browse(
    keyword: Optional[str] = None,
    sort_by: str = "price",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    result = products

    if keyword:
        result = [p for p in result if keyword.lower() in p["name"].lower()]

    reverse = True if order == "desc" else False
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse)

    start = (page - 1) * limit
    paginated = result[start:start + limit]

    return {
        "total": len(result),
        "page": page,
        "data": paginated
    }