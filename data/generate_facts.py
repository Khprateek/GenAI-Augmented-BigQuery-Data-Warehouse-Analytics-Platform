"""
Generates transactional / fact tables for the quick-commerce data warehouse:
  1. orders.csv       (50,000 rows)   - Order headers, payment, delivery SLA, basket financials
  2. order_items.csv  (~180,000 rows) - Line-item granularity, quantity, unit price, substitutions
  3. order_issues.csv (~1,300 rows)   - Post-delivery complaints, resolutions & refunds (~3% rate)
  4. events.csv       (~300,000 rows) - Session clickstream funnel (page_view -> add_to_cart -> purchase)

Depends on: data/raw/dimensions/*.csv (dark_stores, delivery_partners, customers, products)
Run: python data/generate_facts.py
Output: data/raw/facts/*.csv
"""

import csv
import random
from pathlib import Path
from datetime import date, datetime, timedelta
from faker import Faker

fake = Faker('en_IN')
random.seed(42)
Faker.seed(42)

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
DIMENSIONS_DIR = RAW_DIR / "dimensions"
FACTS_DIR = RAW_DIR / "facts"

FACTS_DIR.mkdir(parents=True, exist_ok=True)

N_ORDERS = 50_000
N_SESSIONS = 100_000  # yields ~300,000 events

START_DATE = date(2023, 1, 1)
TODAY = date(2026, 7, 24)
END_DATE = TODAY
DATE_RANGE_DAYS = (END_DATE - START_DATE).days

PAYMENT_METHODS = ["UPI", "UPI", "UPI", "UPI", "UPI", "UPI", "Card", "Card", "Wallet", "Wallet", "COD"]
PLATFORM = ["App"] * 9 + ["Web"] * 1
ORDER_STATUSES = ["DELIVERED"] * 17 + ["CANCELLED"] * 2 + ["FAILED_DELIVERY"] * 1
DELIVERY_PROMISES_MIN = [10, 10, 10, 12, 15, 15, 19]

ISSUE_TYPES = ["Damaged item", "Wrong item delivered", "Item missing", "Expired product", "Poor quality"]
RESOLUTIONS = ["Refund", "Refund", "Replacement", "Wallet Credit"]

HOUR_WEIGHTS = [
    1, 1, 1, 1, 1, 2,      # 12am-5am
    4, 7, 8, 6, 5, 6,      # 6am-11am
    9, 8, 5, 4, 4, 5,      # 12pm-5pm
    8, 10, 9, 7, 5, 3,     # 6pm-11pm
]


def build_promo_calendar(start: date, end: date) -> set:
    promo_dates = set()
    current = start
    while current <= end:
        if current.day in (1, 2, 15, 16):
            promo_dates.add(current)
        next_month_first = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        last_day_of_month = (next_month_first - timedelta(days=1)).day
        if current.day >= last_day_of_month - 1:
            promo_dates.add(current)
        current += timedelta(days=1)

    current = start
    while current <= end:
        if random.random() < 0.03:
            promo_dates.add(current)
        current += timedelta(days=1)

    return promo_dates


PROMO_DATES = build_promo_calendar(START_DATE, END_DATE)
ALL_DATES = [START_DATE + timedelta(days=i) for i in range(DATE_RANGE_DAYS + 1)]
DATE_WEIGHTS = [2.2 if d in PROMO_DATES else 1.0 for d in ALL_DATES]


def weighted_order_date() -> date:
    return random.choices(ALL_DATES, weights=DATE_WEIGHTS, k=1)[0]


def weighted_hour_time(d: date) -> datetime:
    hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
    minute = random.randint(0, 59)
    return datetime.combine(d, datetime.min.time()) + timedelta(hours=hour, minutes=minute)


def load_dimensions():
    """Reads dimension CSVs to ensure foreign key integrity."""
    required_files = ["dark_stores.csv", "delivery_partners.csv", "customers.csv", "products.csv"]
    for fname in required_files:
        if not (DIMENSIONS_DIR / fname).exists():
            print(f"[INFO] Missing {fname}. Generating dimension tables first...")
            from data.generate_dimensions import generate_dimensions
            generate_dimensions()
            break

    # Read dark stores
    dark_stores = []
    store_lookup = {}
    city_store_ids = {}
    with open(DIMENSIONS_DIR / "dark_stores.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["demand_multiplier"] = float(row.get("demand_multiplier", 1.0))
            dark_stores.append(row)
            store_lookup[row["store_id"]] = row
            city_store_ids.setdefault(row["city"], []).append(row["store_id"])

    # Read delivery partners
    rider_lookup_by_store = {sid: [] for sid in store_lookup}
    with open(DIMENSIONS_DIR / "delivery_partners.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rider_lookup_by_store.setdefault(row["store_id"], []).append(row["rider_id"])

    # Read customers
    customers = []
    with open(DIMENSIONS_DIR / "customers.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["is_pass_member"] = row.get("is_pass_member", "False").lower() in ("true", "1")
            customers.append(row)

    # Read products
    products = []
    product_price_map = {}
    with open(DIMENSIONS_DIR / "products.csv", mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["product_id"]
            products.append(row)
            product_price_map[pid] = (float(row["selling_price"]), float(row["cost_price"]))

    return dark_stores, store_lookup, city_store_ids, rider_lookup_by_store, customers, products, product_price_map


def generate_facts():
    print("=" * 60)
    print("Generating Quick-Commerce Transactional / Fact Tables")
    print(f"Target Directory: {FACTS_DIR}")
    print("=" * 60)

    (dark_stores, store_lookup, city_store_ids,
     rider_lookup_by_store, customers, products, product_price_map) = load_dimensions()

    product_ids = [p["product_id"] for p in products]
    customer_ids = [c["customer_id"] for c in customers]

    customer_weights = [
        (3 if c["is_pass_member"] else 1) * store_lookup[c["home_store_id"]]["demand_multiplier"]
        for c in customers
    ]

    print("Generating orders + order_items...")
    orders = []
    order_items = []
    item_counter = 1

    for i in range(1, N_ORDERS + 1):
        order_id = f"ORD{i:07d}"
        customer = random.choices(customers, weights=customer_weights, k=1)[0]

        if random.random() < 0.85:
            store_id = customer["home_store_id"]
        else:
            store_id = random.choice(city_store_ids.get(customer["city"], [customer["home_store_id"]]))

        order_date = weighted_order_date()
        is_promo_day = order_date in PROMO_DATES
        order_dt = weighted_hour_time(order_date)

        status = random.choice(ORDER_STATUSES)
        payment_method = random.choice(PAYMENT_METHODS)
        platform = random.choice(PLATFORM)
        promised_minutes = random.choice(DELIVERY_PROMISES_MIN)

        if status == "DELIVERED":
            actual_minutes = max(4, promised_minutes + round(random.gauss(0, 4)))
            store_riders = rider_lookup_by_store.get(store_id, [])
            rider_id = random.choice(store_riders) if store_riders else "RIDER000001"
            is_on_time = actual_minutes <= promised_minutes + 2
        else:
            actual_minutes = ""
            rider_id = ""
            is_on_time = ""

        n_items = random.randint(2, 8) if is_promo_day else random.randint(1, 6)
        chosen_products = random.sample(product_ids, min(n_items, len(product_ids)))

        order_revenue = 0.0
        for pid in chosen_products:
            selling_price, _ = product_price_map[pid]
            qty = random.randint(1, 3)
            unit_price = round(selling_price * random.uniform(0.95, 1.05), 2)
            is_substituted = (status == "DELIVERED") and (random.random() < 0.03)
            order_items.append({
                "order_item_id": f"ITEM{item_counter:08d}",
                "order_id": order_id,
                "product_id": pid,
                "quantity": qty,
                "unit_price": unit_price,
                "is_substituted": is_substituted,
            })
            order_revenue += qty * unit_price
            item_counter += 1

        if is_promo_day:
            discount_pct = random.choices([0, 0.10, 0.15, 0.20, 0.25], weights=[15, 25, 25, 20, 15])[0]
        else:
            discount_pct = random.choices([0, 0.05, 0.10], weights=[70, 20, 10])[0]
        discount = round(order_revenue * discount_pct, 2)
        delivery_fee = 0 if customer["is_pass_member"] else random.choice([0, 15, 25, 29])

        orders.append({
            "order_id": order_id,
            "customer_id": customer["customer_id"],
            "store_id": store_id,
            "rider_id": rider_id,
            "order_datetime": order_dt.isoformat(),
            "is_promo_day": is_promo_day,
            "status": status,
            "payment_method": payment_method,
            "platform": platform,
            "promised_delivery_minutes": promised_minutes,
            "actual_delivery_minutes": actual_minutes,
            "is_on_time": is_on_time,
            "item_count": n_items,
            "revenue": round(order_revenue, 2),
            "discount": discount,
            "delivery_fee": delivery_fee,
        })

    with open(FACTS_DIR / "orders.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=orders[0].keys())
        writer.writeheader()
        writer.writerows(orders)
    print(f"  [OK] orders.csv ({len(orders):,} rows)")

    with open(FACTS_DIR / "order_items.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=order_items[0].keys())
        writer.writeheader()
        writer.writerows(order_items)
    print(f"  [OK] order_items.csv ({len(order_items):,} rows)")

    # Order Issues
    print("Generating order issues...")
    delivered_orders = [o for o in orders if o["status"] == "DELIVERED"]
    issue_sample = random.sample(delivered_orders, k=int(len(delivered_orders) * 0.03))

    order_issues = []
    for i, o in enumerate(issue_sample, start=1):
        related_items = [it for it in order_items if it["order_id"] == o["order_id"]]
        if not related_items:
            continue
        item = random.choice(related_items)
        reported_at = datetime.fromisoformat(o["order_datetime"]) + timedelta(hours=random.randint(1, 20))
        resolution = random.choice(RESOLUTIONS)

        order_issues.append({
            "issue_id": f"ISSUE{i:06d}",
            "order_id": o["order_id"],
            "product_id": item["product_id"],
            "reported_at": reported_at.isoformat(),
            "issue_type": random.choice(ISSUE_TYPES),
            "resolution": resolution,
            "resolved_same_day": True,
            "refund_amount": round(float(item["unit_price"]) * int(item["quantity"]), 2)
                              if resolution in ("Refund", "Wallet Credit") else 0,
        })

    with open(FACTS_DIR / "order_issues.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=order_issues[0].keys())
        writer.writeheader()
        writer.writerows(order_issues)
    print(f"  [OK] order_issues.csv ({len(order_issues):,} rows)")

    # Events (session-based funnel)
    print("Generating events (session funnel)...")
    STAGE_CONVERSION = {
        "add_to_cart": 0.42,
        "begin_checkout": 0.70,
        "reorder_click": 0.12,
        "purchase": 0.78,
    }

    events = []
    event_id = 1
    for _ in range(N_SESSIONS):
        session_customer = random.choice(customer_ids) if random.random() > 0.15 else ""
        session_date = weighted_order_date()
        base_ts = weighted_hour_time(session_date)

        events.append({
            "event_id": f"EVT{event_id:08d}",
            "customer_id": session_customer,
            "event_type": "page_view",
            "event_timestamp": base_ts.isoformat(),
        })
        event_id += 1

        if random.random() < STAGE_CONVERSION["add_to_cart"]:
            cart_ts = base_ts + timedelta(minutes=random.randint(1, 6))
            events.append({
                "event_id": f"EVT{event_id:08d}",
                "customer_id": session_customer,
                "event_type": "add_to_cart",
                "event_timestamp": cart_ts.isoformat(),
            })
            event_id += 1

            if random.random() < STAGE_CONVERSION["reorder_click"]:
                reorder_ts = cart_ts + timedelta(minutes=random.randint(1, 3))
                events.append({
                    "event_id": f"EVT{event_id:08d}",
                    "customer_id": session_customer,
                    "event_type": "reorder_click",
                    "event_timestamp": reorder_ts.isoformat(),
                })
                event_id += 1

            if random.random() < STAGE_CONVERSION["begin_checkout"]:
                checkout_ts = cart_ts + timedelta(minutes=random.randint(1, 4))
                events.append({
                    "event_id": f"EVT{event_id:08d}",
                    "customer_id": session_customer,
                    "event_type": "begin_checkout",
                    "event_timestamp": checkout_ts.isoformat(),
                })
                event_id += 1

                if random.random() < STAGE_CONVERSION["purchase"]:
                    purchase_ts = checkout_ts + timedelta(minutes=random.randint(1, 10))
                    events.append({
                        "event_id": f"EVT{event_id:08d}",
                        "customer_id": session_customer,
                        "event_type": "purchase",
                        "event_timestamp": purchase_ts.isoformat(),
                    })
                    event_id += 1

    with open(FACTS_DIR / "events.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=events[0].keys())
        writer.writeheader()
        writer.writerows(events)
    print(f"  [OK] events.csv ({len(events):,} rows)")

    print("\n[SUCCESS] Transactional/Fact tables generation complete!")
    print(f"Files saved in: {FACTS_DIR}")


if __name__ == "__main__":
    generate_facts()
