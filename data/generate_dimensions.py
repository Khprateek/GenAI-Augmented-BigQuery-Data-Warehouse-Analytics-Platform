"""
Generates static master / dimension tables for the quick-commerce data warehouse:
  1. dark_stores.csv       (~59 rows)    - Micro-fulfilment center locations & demand tiers
  2. delivery_partners.csv (~1,500 rows) - Rider partner profiles & assigned dark stores
  3. customers.csv         (20,000 rows) - Customer profiles & Zepto Pass memberships
  4. products.csv          (5,000 rows)  - Grocery/daily essentials catalog & pricing
  5. marketing_spend.csv   (~9,000 rows) - Daily marketing spend per acquisition channel

Run: python data/generate_dimensions.py
Output: data/raw/dimensions/*.csv
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
DIMENSIONS_DIR.mkdir(parents=True, exist_ok=True)

N_CUSTOMERS = 20_000
N_PRODUCTS = 5_000

START_DATE = date(2023, 1, 1)
TODAY = date(2026, 7, 24)
END_DATE = TODAY
DATE_RANGE_DAYS = (END_DATE - START_DATE).days

# ── CITIES & LOCALITIES ───────────────────────────────────────────────────────
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

# ── PRODUCT CATALOG DEFINITION ────────────────────────────────────────────────
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

VEHICLE_TYPES = ["Electric Scooter", "Electric Scooter", "Bike", "Bicycle"]

MARKETING_CHANNELS = ["performance_meta", "performance_google", "influencer", "referral_program", "offline_hyperlocal"]
BASE_SPEND_INR = {
    "performance_meta": 45_000,
    "performance_google": 35_000,
    "influencer": 15_000,
    "referral_program": 8_000,
    "offline_hyperlocal": 10_000,
}
CPC_RANGE_INR = {
    "performance_meta": (5, 9),
    "performance_google": (4, 8),
    "influencer": (2, 5),
    "referral_program": (0.5, 2),
    "offline_hyperlocal": (1, 3),
}


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


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


def generate_dimensions():
    print("=" * 60)
    print("Generating Quick-Commerce Master / Dimension Tables")
    print(f"Target Directory: {DIMENSIONS_DIR}")
    print("=" * 60)

    # 1. Dark Stores
    print("Generating dark stores...")
    dark_stores = []
    store_lookup = {}
    for city, info in CITY_INFO.items():
        for idx, locality in enumerate(info["localities"]):
            store_id = f"{info['code']}-{locality.replace(' ', '').replace('-', '')}"
            launch = random_date(START_DATE, START_DATE + timedelta(days=DATE_RANGE_DAYS // 2))
            
            if idx == 0:
                demand_tier = "flagship"
                demand_multiplier = round(random.uniform(2.6, 3.4), 2)
            else:
                demand_tier = random.choices(["high", "medium", "low"], weights=[20, 45, 35])[0]
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

    with open(DIMENSIONS_DIR / "dark_stores.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dark_stores[0].keys())
        writer.writeheader()
        writer.writerows(dark_stores)
    print(f"  [OK] dark_stores.csv ({len(dark_stores):,} rows)")

    # 2. Delivery Partners
    print("Generating delivery partners...")
    delivery_partners = []
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
            rider_num += 1

    with open(DIMENSIONS_DIR / "delivery_partners.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=delivery_partners[0].keys())
        writer.writeheader()
        writer.writerows(delivery_partners)
    print(f"  [OK] delivery_partners.csv ({len(delivery_partners):,} rows)")

    # 3. Customers
    print("Generating customers...")
    all_store_ids = list(store_lookup.keys())
    store_choice_weights = [store_lookup[sid]["demand_multiplier"] for sid in all_store_ids]
    customers = []
    for i in range(1, N_CUSTOMERS + 1):
        signup = random_date(START_DATE, END_DATE)
        home_store_id = random.choices(all_store_ids, weights=store_choice_weights, k=1)[0]
        store = store_lookup[home_store_id]
        is_pass_member = random.random() < 0.25
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

    with open(DIMENSIONS_DIR / "customers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=customers[0].keys())
        writer.writeheader()
        writer.writerows(customers)
    print(f"  [OK] customers.csv ({len(customers):,} rows)")

    # 4. Products
    print("Generating products...")
    products = []
    for i in range(1, N_PRODUCTS + 1):
        category = random.choice(list(CATEGORIES.keys()))
        brand = random.choice(CATEGORIES[category])
        pack_size = random.choice(PACK_SIZES_BY_CATEGORY[category])
        lo, hi = PRICE_RANGE_BY_CATEGORY[category]
        selling_price = round(random.uniform(lo, hi), 2)
        mrp = round(selling_price * random.uniform(1.0, 1.20), 2)
        cost_price = round(selling_price * random.uniform(0.75, 0.90), 2)
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

    with open(DIMENSIONS_DIR / "products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=products[0].keys())
        writer.writeheader()
        writer.writerows(products)
    print(f"  [OK] products.csv ({len(products):,} rows)")

    # 5. Marketing Spend
    print("Generating marketing spend...")
    marketing_spend = []
    spend_id = 1
    current = START_DATE
    while current <= END_DATE:
        is_promo_day = current in PROMO_DATES
        for channel in MARKETING_CHANNELS:
            base = BASE_SPEND_INR[channel]
            spend_multiplier = random.uniform(1.3, 1.8) if is_promo_day else random.uniform(0.6, 1.1)
            spend = round(base * spend_multiplier, 2)

            cpc_lo, cpc_hi = CPC_RANGE_INR[channel]
            cpc = random.uniform(cpc_lo, cpc_hi)
            clicks = max(1, int(spend / cpc))
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

    with open(DIMENSIONS_DIR / "marketing_spend.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=marketing_spend[0].keys())
        writer.writeheader()
        writer.writerows(marketing_spend)
    print(f"  [OK] marketing_spend.csv ({len(marketing_spend):,} rows)")

    print("\n[SUCCESS] Master/Dimension tables generation complete!")
    print(f"Files saved in: {DIMENSIONS_DIR}")


if __name__ == "__main__":
    generate_dimensions()
