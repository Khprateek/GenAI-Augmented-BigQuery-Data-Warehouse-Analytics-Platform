"""
Generates a Zepto-inspired quick-commerce dataset for the analytics warehouse.

Modeled on how Indian quick-commerce (10-20 minute delivery) actually works:
dark stores instead of warehouses, riders instead of generic "channels",
delivery-time as the core KPI, grocery/daily-essentials catalog, INR pricing,
and a customer base confined to the metro/tier-1 cities this business model
actually serves (not all of India).

Tables produced:
  dark_stores.csv         ~59 rows    (micro-fulfilment centers)
  delivery_partners.csv  ~1,500 rows  (riders)
  customers.csv            20,000 rows
  products.csv              5,000 rows
  orders.csv                50,000 rows
  order_items.csv         ~180,000 rows
  order_issues.csv         ~1,300 rows  (same-day resolution, no "return shipping")
  events.csv              ~300,000 rows (session-based funnel)
  marketing_spend.csv       ~9,000 rows

Run:  python generate_data.py
Output: ./raw2/*.csv
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
OUT_DIR = BASE_DIR / "raw2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_CUSTOMERS = 20_000
N_PRODUCTS = 5_000
N_ORDERS = 50_000
N_SESSIONS = 100_000  # each session yields 1-3 events -> ~300k events, same as before

START_DATE = date(2023, 1, 1)

# TODAY anchors the dataset to "now" so nothing generates into the future.
# Match this to whatever date your dashboard is meant to represent "as of".
TODAY = date(2026, 7, 24)
END_DATE = TODAY  # was date(2026, 8, 1) - capped so no future-dated rows

DATE_RANGE_DAYS = (END_DATE - START_DATE).days

# ── CITIES ───────────────────────────────────────────────────────────────────
CITY_INFO = {
    "Mumbai":     {"code": "MUM", "state": "Maharashtra",    "lat": 19.0760, "lon": 72.8777,
                    "localities": ["Andheri", "Bandra", "Powai", "Malad", "Chembur"]},
    "Delhi":      {"code": "DEL", "state": "Delhi",          "lat": 28.7041, "lon": 77.1025,
                    "localities": ["Saket", "Dwarka", "Rohini", "Karol Bagh", "Vasant Kunj"]},
    "Bengaluru":  {"code": "BLR", "state": "Karnataka",      "lat": 12.9716, "lon": 77.5946,
                    "localities": ["Koramangala", "Indiranagar", "Whitefield", "HSR Layout", "Jayanagar"]},
    "Hyderabad":  {"code": "HYD", "state": "Telangana",      "lat": 17.3850, "lon": 78.4867,
                    "localities": ["Gachibowli", "Banjara Hills", "Kukatpally", "Madhapur"]},
    "Pune":       {"code": "PUN", "state": "Maharashtra",    "lat": 18.5204, "lon": 73.8567,
                    "localities": ["Kothrud", "Viman Nagar", "Hinjewadi", "Baner"]},
    "Chennai":    {"code": "CHE", "state": "Tamil Nadu",     "lat": 13.0827, "lon": 80.2707,
                    "localities": ["T Nagar", "Anna Nagar", "Velachery", "Adyar"]},
    "Kolkata":    {"code": "KOL", "state": "West Bengal",    "lat": 22.5726, "lon": 88.3639,
                    "localities": ["Salt Lake", "Park Street", "Ballygunge", "Behala"]},
    "Ahmedabad":  {"code": "AMD", "state": "Gujarat",        "lat": 23.0225, "lon": 72.5714,
                    "localities": ["Satellite", "Navrangpura", "Bopal", "Maninagar"]},
    "Jaipur":     {"code": "JAI", "state": "Rajasthan",      "lat": 26.9124, "lon": 75.7873,
                    "localities": ["Malviya Nagar", "Vaishali Nagar", "C Scheme"]},
    "Lucknow":    {"code": "LKO", "state": "Uttar Pradesh",  "lat": 26.8467, "lon": 80.9462,
                    "localities": ["Gomti Nagar", "Hazratganj", "Indira Nagar"]},
    "Chandigarh": {"code": "CHD", "state": "Chandigarh",     "lat": 30.7333, "lon": 76.7794,
                    "localities": ["Sector 17", "Sector 22", "Sector 35"]},
    "Surat":      {"code": "SUR", "state": "Gujarat",        "lat": 21.1702, "lon": 72.8311,
                    "localities": ["Adajan", "Vesu", "Citylight"]},
    "Indore":     {"code": "IND", "state": "Madhya Pradesh", "lat": 22.7196, "lon": 75.8577,
                    "localities": ["Vijay Nagar", "Palasia", "Rajendra Nagar"]},
    "Coimbatore": {"code": "CBE", "state": "Tamil Nadu",     "lat": 11.0168, "lon": 76.9558,
                    "localities": ["RS Puram", "Gandhipuram", "Peelamedu"]},
    "Kochi":      {"code": "KOC", "state": "Kerala",         "lat": 9.9312,  "lon": 76.2673,
                    "localities": ["Kakkanad", "Edappally", "Vytila"]},
    "Nagpur":     {"code": "NAG", "state": "Maharashtra",    "lat": 21.1458, "lon": 79.0882,
                    "localities": ["Dharampeth", "Sadar", "Civil Lines"]},
}

# ── CATALOG: grocery / daily-essentials categories, not general e-comm ───────
CATEGORIES = {
    "Fruits & Vegetables": ["FarmFresh", "GreenHarvest", "Harvest Valley", "PureField"],
    "Dairy & Breakfast":   ["MorningDew Dairy", "GoldenCow", "DailyFresh", "SunriseFarms"],
    "Snacks & Munchies":   ["CrispKing", "MunchBox", "Namkeen Junction", "SnackVilla"],
    "Beverages":           ["ChillSip", "FizzUp", "PureSip", "Brewhouse"],
    "Personal Care":       ["GlowNatural", "CleanEssence", "DailyCare", "Barefoot Botanics"],
    "Home & Cleaning":     ["SparklePro", "HomeShine", "CleanNest", "FreshHome"],
    "Baby Care":           ["LittleSteps", "TinyCare", "BabyNest", "SoftCloud"],
    "Atta, Rice & Dal":    ["WholeGrain Mills", "Daily Grain Co", "Harvest Mill", "GrainCraft"],
    "Frozen & Ice Cream":  ["FrostBite", "ChillTreat", "IceCraft", "ArcticBite"],
    "Bakery":              ["CrustCraft", "BreadHouse", "GoldenCrust", "OvenFresh"],
    "Meat, Fish & Eggs":   ["FreshCatch", "PureProtein", "FarmEgg Co", "MeatCraft"],
    "Pharmacy & Wellness": ["WellCare", "MediPlus", "HealthFirst", "CareWell"],
}
PERISHABLE_CATEGORIES = {"Fruits & Vegetables", "Dairy & Breakfast", "Bakery", "Meat, Fish & Eggs"}

PACK_SIZES_BY_CATEGORY = {
    "Fruits & Vegetables": ["250 g", "500 g", "1 kg"],
    "Dairy & Breakfast":   ["200 ml", "500 ml", "1 L", "400 g"],
    "Snacks & Munchies":   ["50 g", "100 g", "200 g"],
    "Beverages":           ["250 ml", "500 ml", "1 L", "2 L"],
    "Personal Care":       ["50 ml", "100 ml", "200 ml", "1 unit"],
    "Home & Cleaning":     ["500 ml", "1 L", "1 unit"],
    "Baby Care":           ["1 unit", "1 pack"],
    "Atta, Rice & Dal":    ["1 kg", "5 kg", "10 kg"],
    "Frozen & Ice Cream":  ["500 ml", "700 ml", "1 kg"],
    "Bakery":              ["200 g", "400 g", "1 unit"],
    "Meat, Fish & Eggs":   ["250 g", "500 g", "6 pcs", "12 pcs"],
    "Pharmacy & Wellness": ["1 strip", "1 bottle", "1 unit"],
}

PRICE_RANGE_BY_CATEGORY = {
    "Fruits & Vegetables": (15, 150),
    "Dairy & Breakfast":   (20, 350),
    "Snacks & Munchies":   (10, 250),
    "Beverages":           (15, 300),
    "Personal Care":       (40, 600),
    "Home & Cleaning":     (30, 500),
    "Baby Care":           (50, 900),
    "Atta, Rice & Dal":    (40, 700),
    "Frozen & Ice Cream":  (50, 450),
    "Bakery":              (20, 200),
    "Meat, Fish & Eggs":   (60, 600),
    "Pharmacy & Wellness": (30, 800),
}

PAYMENT_METHODS = ["UPI", "UPI", "UPI", "UPI", "UPI", "UPI", "Card", "Card", "Wallet", "Wallet", "COD"]
PLATFORM = ["App"] * 9 + ["Web"] * 1
ORDER_STATUSES = ["DELIVERED"] * 17 + ["CANCELLED"] * 2 + ["FAILED_DELIVERY"] * 1
DELIVERY_PROMISES_MIN = [10, 10, 10, 12, 15, 15, 19]  # minutes
VEHICLE_TYPES = ["Electric Scooter", "Electric Scooter", "Bike", "Bicycle"]

ISSUE_TYPES = ["Damaged item", "Wrong item delivered", "Item missing", "Expired product", "Poor quality"]
RESOLUTIONS = ["Refund", "Refund", "Replacement", "Wallet Credit"]

MARKETING_CHANNELS = ["performance_meta", "performance_google", "influencer", "referral_program", "offline_hyperlocal"]
BASE_SPEND_INR = {
    "performance_meta": 45_000,
    "performance_google": 35_000,
    "influencer": 15_000,
    "referral_program": 8_000,
    "offline_hyperlocal": 10_000,
}
# Rough cost-per-click by channel (INR) - used so clicks scale with spend,
# not just be drawn from the same fixed range for every channel.
CPC_RANGE_INR = {
    "performance_meta": (5, 9),
    "performance_google": (4, 8),
    "influencer": (2, 5),
    "referral_program": (0.5, 2),
    "offline_hyperlocal": (1, 3),
}

# Rough hourly demand shape: quiet overnight, breakfast bump, lunch peak, evening peak
HOUR_WEIGHTS = [
    1, 1, 1, 1, 1, 2,      # 12am-5am
    4, 7, 8, 6, 5, 6,      # 6am-11am
    9, 8, 5, 4, 4, 5,      # 12pm-5pm
    8, 10, 9, 7, 5, 3,     # 6pm-11pm
]


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_datetime(start: date, end: date) -> datetime:
    d = random_date(start, end)
    return datetime.combine(d, datetime.min.time()) + timedelta(
        hours=random.randint(0, 23), minutes=random.randint(0, 59)
    )


def weighted_hour_time(d: date) -> datetime:
    hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
    minute = random.randint(0, 59)
    return datetime.combine(d, datetime.min.time()) + timedelta(hours=hour, minutes=minute)


# ── PROMO CALENDAR ──────────────────────────────────────────────────────────
# Gives discount and order volume a real causal link instead of both being
# drawn independently. Promo days = payday sales (1st/2nd, 15th/16th),
# month-end clearance (last 2 days of month), plus a random sprinkle of
# festival-style flash sales (~3% of days).
def build_promo_calendar(start: date, end: date) -> set:
    promo_dates = set()
    current = start
    while current <= end:
        if current.day in (1, 2, 15, 16):
            promo_dates.add(current)
        # last 2 days of the month
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
# Promo days get ~2.2x the odds of an order landing on them - demand surges
# on sale days, same as real quick-commerce traffic patterns.
DATE_WEIGHTS = [2.2 if d in PROMO_DATES else 1.0 for d in ALL_DATES]


def weighted_order_date() -> date:
    return random.choices(ALL_DATES, weights=DATE_WEIGHTS, k=1)[0]


# ── DARK STORES ────────────────────────────────────────────────────────────
print("Generating dark stores...")
dark_stores = []
store_lookup = {}
city_store_ids = {}

for city, info in CITY_INFO.items():
    city_store_ids[city] = []
    for idx, locality in enumerate(info["localities"]):
        store_id = f"{info['code']}-{locality.replace(' ', '').replace('-', '')}"
        launch = random_date(START_DATE, START_DATE + timedelta(days=DATE_RANGE_DAYS // 2))
        
        if idx == 0:
            demand_tier = "flagship"
            demand_multiplier = round(random.uniform(2.6, 3.4), 2)
        else:
            demand_tier = random.choices(
                ["high", "medium", "low"], weights=[20, 45, 35]
            )[0]
            demand_multiplier = {
                "high": round(random.uniform(1.5, 2.2), 2),
                "medium": round(random.uniform(0.8, 1.3), 2),
                "low": round(random.uniform(0.3, 0.7), 2),
            }[demand_tier]

        store = {
            "store_id": store_id,
            "city": city,
            "state": info["state"],
            "locality": locality,
            "latitude": round(info["lat"] + random.uniform(-0.05, 0.05), 5),
            "longitude": round(info["lon"] + random.uniform(-0.05, 0.05), 5),
            "sku_capacity": random.randint(2000, 3000),
            "delivery_radius_km": round(random.uniform(1.5, 2.5), 2),
            "launch_date": launch.isoformat(),
            "demand_tier": demand_tier,
            "demand_multiplier": demand_multiplier,
        }
        dark_stores.append(store)
        store_lookup[store_id] = store
        city_store_ids[city].append(store_id)

with open(OUT_DIR / "dark_stores.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=dark_stores[0].keys())
    writer.writeheader()
    writer.writerows(dark_stores)

# ── DELIVERY PARTNERS (riders) ───────────────────────────────────────────────
print("Generating delivery partners...")
delivery_partners = []
rider_lookup_by_store = {sid: [] for sid in store_lookup}
rider_num = 1
for store_id, store in store_lookup.items():
    n_riders = random.randint(15, 35)
    launch_date_val = date.fromisoformat(store["launch_date"])
    for _ in range(n_riders):
        rider_id = f"RIDER{rider_num:06d}"
        join = random_date(launch_date_val, END_DATE)
        delivery_partners.append({
            "rider_id": rider_id,
            "name": fake.name(),
            "store_id": store_id,
            "city": store["city"],
            "vehicle_type": random.choice(VEHICLE_TYPES),
            "join_date": join.isoformat(),
        })
        rider_lookup_by_store[store_id].append(rider_id)
        rider_num += 1

with open(OUT_DIR / "delivery_partners.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=delivery_partners[0].keys())
    writer.writeheader()
    writer.writerows(delivery_partners)

# ── CUSTOMERS ────────────────────────────────────────────────────────────────
print("Generating customers...")
all_store_ids = list(store_lookup.keys())
store_choice_weights = [store_lookup[sid]["demand_multiplier"] for sid in all_store_ids]
customers = []
for i in range(1, N_CUSTOMERS + 1):
    # Capped at END_DATE (== TODAY) so no customer signs up "in the future".
    signup = random_date(START_DATE, END_DATE)
    home_store_id = random.choices(all_store_ids, weights=store_choice_weights, k=1)[0]
    store = store_lookup[home_store_id]
    is_pass_member = random.random() < 0.25  # Zepto Pass-style subscription
    customers.append({
        "customer_id": f"CUST{i:06d}",
        "name": fake.name(),
        "email": fake.unique.email(),
        "city": store["city"],
        "state": store["state"],
        "home_locality": store["locality"],
        "home_store_id": home_store_id,
        "is_pass_member": is_pass_member,
        "signup_date": signup.isoformat(),
    })

with open(OUT_DIR / "customers.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=customers[0].keys())
    writer.writeheader()
    writer.writerows(customers)

# ── PRODUCTS ─────────────────────────────────────────────────────────────────
print("Generating products...")
products = []
product_price_map = {}
for i in range(1, N_PRODUCTS + 1):
    category = random.choice(list(CATEGORIES.keys()))
    brand = random.choice(CATEGORIES[category])
    pack_size = random.choice(PACK_SIZES_BY_CATEGORY[category])
    lo, hi = PRICE_RANGE_BY_CATEGORY[category]
    selling_price = round(random.uniform(lo, hi), 2)
    mrp = round(selling_price * random.uniform(1.0, 1.20), 2)
    cost_price = round(selling_price * random.uniform(0.75, 0.90), 2)  # thin grocery margins
    is_perishable = category in PERISHABLE_CATEGORIES
    shelf_life_days = random.randint(1, 10) if is_perishable else random.randint(60, 540)

    product_id = f"PROD{i:06d}"
    products.append({
        "product_id": product_id,
        "product_name": f"{brand} {fake.word().capitalize()} {fake.word().capitalize()}",
        "category": category,
        "brand": brand,
        "pack_size": pack_size,
        "mrp": mrp,
        "selling_price": selling_price,
        "cost_price": cost_price,
        "is_perishable": is_perishable,
        "shelf_life_days": shelf_life_days,
    })
    product_price_map[product_id] = (selling_price, cost_price)

with open(OUT_DIR / "products.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=products[0].keys())
    writer.writeheader()
    writer.writerows(products)

product_ids = [p["product_id"] for p in products]

# ── ORDERS + ORDER_ITEMS ─────────────────────────────────────────────────────
print("Generating orders + order_items...")
orders = []
order_items = []
item_counter = 1
customer_weights = [
    (3 if c["is_pass_member"] else 1) * store_lookup[c["home_store_id"]]["demand_multiplier"]
    for c in customers
]  # pass members order more; customers at high-demand stores order more too

for i in range(1, N_ORDERS + 1):
    order_id = f"ORD{i:07d}"
    customer = random.choices(customers, weights=customer_weights, k=1)[0]

    # ~85% fulfilled by the customer's home store, ~15% by another store in the same city
    if random.random() < 0.85:
        store_id = customer["home_store_id"]
    else:
        store_id = random.choice(city_store_ids[customer["city"]])

    order_date = weighted_order_date()
    is_promo_day = order_date in PROMO_DATES
    order_dt = weighted_hour_time(order_date)

    status = random.choice(ORDER_STATUSES)
    payment_method = random.choice(PAYMENT_METHODS)
    platform = random.choice(PLATFORM)
    promised_minutes = random.choice(DELIVERY_PROMISES_MIN)

    if status == "DELIVERED":
        actual_minutes = max(4, promised_minutes + round(random.gauss(0, 4)))
        rider_id = random.choice(rider_lookup_by_store[store_id])
        is_on_time = actual_minutes <= promised_minutes + 2
    else:
        actual_minutes = ""
        rider_id = ""
        is_on_time = ""

    # Basket size grows on promo days - real quick-commerce sale-day behavior.
    n_items = random.randint(2, 8) if is_promo_day else random.randint(1, 6)
    chosen_products = random.sample(product_ids, min(n_items, len(product_ids)))

    order_revenue = 0.0
    for pid in chosen_products:
        selling_price, _ = product_price_map[pid]
        qty = random.randint(1, 3)
        unit_price = round(selling_price * random.uniform(0.95, 1.05), 2)  # minor price drift
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

    # Discount rate is now tied to whether this is a promo day: higher and
    # more frequent discounts on sale days, mostly none on regular days.
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

with open(OUT_DIR / "orders.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=orders[0].keys())
    writer.writeheader()
    writer.writerows(orders)

with open(OUT_DIR / "order_items.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=order_items[0].keys())
    writer.writeheader()
    writer.writerows(order_items)

customer_ids = [c["customer_id"] for c in customers]

# ── ORDER ISSUES (replaces returns.csv) ───────────────────────────────────────
print("Generating order issues...")
delivered_orders = [o for o in orders if o["status"] == "DELIVERED"]
issue_sample = random.sample(delivered_orders, k=int(len(delivered_orders) * 0.03))  # ~3% issue rate

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

with open(OUT_DIR / "order_issues.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=order_issues[0].keys())
    writer.writeheader()
    writer.writerows(order_issues)

# ── EVENTS (session-based funnel) ────────────────────────────────────────────
# Each "session" is a page_view that may (or may not) progress to add_to_cart,
# then may (or may not) progress to purchase. This guarantees the funnel is
# monotonically decreasing: page_view >= add_to_cart >= purchase, unlike
# independently-sampled event types which produced an impossible funnel.
print("Generating events (session-based funnel)...")
STAGE_CONVERSION = {
    "add_to_cart": 0.42,   # 42% of sessions add something to cart
    "begin_checkout": 0.70, # 70% of add-to-cart sessions go to checkout
    "reorder_click": 0.12,  # 12% of add-to-cart sessions use the reorder shortcut
    "purchase": 0.78,      # 78% of checkout sessions go on to purchase
}

events = []
event_id = 1
for _ in range(N_SESSIONS):
    session_customer = random.choice(customer_ids) if random.random() > 0.15 else ""
    session_date = weighted_order_date()  # sessions also spike on promo days
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

with open(OUT_DIR / "events.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=events[0].keys())
    writer.writeheader()
    writer.writerows(events)

# ── MARKETING SPEND — daily spend per (quick-commerce-relevant) channel ──────
print("Generating marketing_spend...")
marketing_spend = []
spend_id = 1
current = START_DATE
while current <= END_DATE:
    is_promo_day = current in PROMO_DATES
    for channel in MARKETING_CHANNELS:
        base = BASE_SPEND_INR[channel]
        # Ad budgets get pushed up around sale days too - campaigns follow demand.
        spend_multiplier = random.uniform(1.3, 1.8) if is_promo_day else random.uniform(0.6, 1.1)
        spend = round(base * spend_multiplier, 2)

        cpc_lo, cpc_hi = CPC_RANGE_INR[channel]
        cpc = random.uniform(cpc_lo, cpc_hi)
        clicks = max(1, int(spend / cpc))  # clicks now scale with actual spend
        impressions = clicks * random.randint(10, 30)
        app_installs = int(clicks * random.uniform(0.02, 0.08))

        marketing_spend.append({
            "spend_id": f"MKT{spend_id:07d}",
            "date": current.isoformat(),
            "channel": channel,
            "is_promo_day": is_promo_day,
            "spend_inr": spend,
            "impressions": impressions,
            "clicks": clicks,
            "app_installs": app_installs,
        })
        spend_id += 1
    current += timedelta(days=1)

with open(OUT_DIR / "marketing_spend.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=marketing_spend[0].keys())
    writer.writeheader()
    writer.writerows(marketing_spend)

print(f"\nDone. Files written to: {OUT_DIR}")
print(f"  dark_stores.csv        {len(dark_stores):>7,} rows")
print(f"  delivery_partners.csv  {len(delivery_partners):>7,} rows")
print(f"  customers.csv           {len(customers):>7,} rows")
print(f"  products.csv            {len(products):>7,} rows")
print(f"  orders.csv              {len(orders):>7,} rows")
print(f"  order_items.csv         {len(order_items):>7,} rows")
print(f"  order_issues.csv        {len(order_issues):>7,} rows")
print(f"  events.csv              {len(events):>7,} rows")
print(f"  marketing_spend.csv     {len(marketing_spend):>7,} rows")
print(f"  promo days in range     {len(PROMO_DATES):>7,} / {len(ALL_DATES):,}")