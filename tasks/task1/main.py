import os
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ── Database setup ──────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/online_store")

engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# ── ORM Models ──────────────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)

    orders = relationship("Order", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_amount = Column(Float, nullable=False, default=0.0)

    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "orderitems"

    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


# ── Initialize schema ──────────────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(engine)
    print("Database schema created successfully.")


# ── Scenario 1: Place an order ─────────────────────────────────────────────────

def place_order(customer_id: int, items: list[dict[int, int]]) -> int:
    """
    Places a new order atomically.
    items: list of dicts with keys 'product_id' and 'quantity'
    Returns the new order_id.
    """
    session = Session()
    try:
        # 1. Create the order record
        order = Order(
            customer_id=customer_id,
            order_date=datetime.utcnow(),
            total_amount=0.0,
        )
        session.add(order)
        session.flush()  # get order_id

        total = 0.0

        # 2. Add order items with subtotals
        for item in items:
            product = session.query(Product).filter(
                Product.product_id == item["product_id"]
            ).first()
            if not product:
                raise ValueError(f"Product with id {item['product_id']} not found.")

            subtotal = product.price * item["quantity"]
            total += subtotal

            order_item = OrderItem(
                order_id=order.order_id,
                product_id=product.product_id,
                quantity=item["quantity"],
                subtotal=subtotal,
            )
            session.add(order_item)

        # 3. Update the order total_amount
        order.total_amount = total

        session.commit()
        print(f"Order placed successfully. Order ID: {order.order_id}, Total: {total:.2f}")
        return order.order_id

    except Exception as e:
        session.rollback()
        print(f"Order placement failed: {e}")
        raise
    finally:
        session.close()


# ── Scenario 2: Update customer email ──────────────────────────────────────────

def update_customer_email(customer_id: int, new_email: str) -> None:
    """
    Atomically updates a customer's email address.
    """
    session = Session()
    try:
        customer = session.query(Customer).filter(
            Customer.customer_id == customer_id
        ).first()
        if not customer:
            raise ValueError(f"Customer with id {customer_id} not found.")

        old_email = customer.email
        customer.email = new_email

        session.commit()
        print(f"Customer {customer_id} email updated: {old_email} -> {new_email}")

    except Exception as e:
        session.rollback()
        print(f"Failed to update customer email: {e}")
        raise
    finally:
        session.close()


# ── Scenario 3: Add a new product ──────────────────────────────────────────────

def add_product(product_name: str, price: float) -> int:
    """
    Atomically adds a new product to the Products table.
    Returns the new product_id.
    """
    session = Session()
    try:
        product = Product(
            product_name=product_name,
            price=price,
        )
        session.add(product)
        session.commit()
        print(f"Product added: '{product_name}' (ID: {product.product_id}, Price: {price:.2f})")
        return product.product_id

    except Exception as e:
        session.rollback()
        print(f"Failed to add product: {e}")
        raise
    finally:
        session.close()


# ── Seed helper ────────────────────────────────────────────────────────────────

def seed_data():
    """Insert sample data if tables are empty."""
    session = Session()
    try:
        if session.query(Customer).count() == 0:
            session.add_all([
                Customer(first_name="Alice", last_name="Smith", email="alice@example.com"),
                Customer(first_name="Bob", last_name="Jones", email="bob@example.com"),
            ])
        if session.query(Product).count() == 0:
            session.add_all([
                Product(product_name="Laptop", price=999.99),
                Product(product_name="Mouse", price=29.99),
                Product(product_name="Keyboard", price=79.99),
            ])
        session.commit()
        print("Seed data inserted.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    seed_data()

    print("\n" + "=" * 60)
    print("SCENARIO 1 — Place an order")
    print("=" * 60)
    order_id = place_order(
        customer_id=1,
        items=[
            {"product_id": 1, "quantity": 1},   # 1 Laptop
            {"product_id": 2, "quantity": 2},   # 2 Mice
            {"product_id": 3, "quantity": 1},   # 1 Keyboard
        ],
    )

    print("\n" + "=" * 60)
    print("SCENARIO 2 — Update customer email")
    print("=" * 60)
    update_customer_email(1, "alice.smith@newmail.com")

    print("\n" + "=" * 60)
    print("SCENARIO 3 — Add a new product")
    print("=" * 60)
    new_pid = add_product("Monitor", price=349.99)

    print("\n" + "=" * 60)
    print("All scenarios completed successfully.")
    print("=" * 60)
