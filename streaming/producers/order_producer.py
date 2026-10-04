"""
Order Event Producer for Quick-Commerce Platform.

Simulates real-time customer checkouts across dark stores.
Publishes events to Kafka topic: quickcommerce.orders
"""

import json
import random
import time
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from confluent_kafka import Producer
from faker import Faker

# Ensure utf-8 output on Windows consoles if possible
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path so we can import streaming.config
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from streaming.config import PRODUCER_CONFIG, TOPIC_ORDERS

fake = Faker("en_IN")

# Sample quick-commerce catalog items
CATALOG = [
    {"product_id": "PRD-MILK-01", "name": "Amul Taaza Homogenised Toned Milk 1L", "category": "Dairy", "price": 54.0},
    {"product_id": "PRD-MILK-02", "name": "Nandini GoodLife Milk 500ml", "category": "Dairy", "price": 28.0},
    {"product_id": "PRD-BRED-01", "name": "Modern Brown Bread 400g", "category": "Bakery", "price": 45.0},
    {"product_id": "PRD-EGGS-01", "name": "Eggoz Farm Fresh White Eggs 6 Pcs", "category": "Eggs & Meat", "price": 60.0},
    {"product_id": "PRD-CURD-01", "name": "Mother Dairy Classic Curd 400g", "category": "Dairy", "price": 35.0},
    {"product_id": "PRD-VEG-01",  "name": "Fresh Onion 1kg", "category": "Fruits & Vegetables", "price": 38.0},
    {"product_id": "PRD-VEG-02",  "name": "Fresh Potato 1kg", "category": "Fruits & Vegetables", "price": 32.0},
    {"product_id": "PRD-VEG-03",  "name": "Hybrid Tomato 500g", "category": "Fruits & Vegetables", "price": 25.0},
    {"product_id": "PRD-SNK-01",  "name": "Lay's India's Magic Masala 50g", "category": "Snacks", "price": 20.0},
    {"product_id": "PRD-BEV-01",  "name": "Coca-Cola 750ml", "category": "Beverages", "price": 40.0},
]

DARK_STORES = [
    "DS-BLR-KORAMANGALA",
    "DS-BLR-INDIRANAGAR",
    "DS-BLR-HSR-LAYOUT",
    "DS-DEL-HAUZ-KHAS",
    "DS-DEL-CONNAUGHT-PLACE",
    "DS-MUM-ANDHERI-WEST",
    "DS-MUM-BANDRA",
]

PAYMENT_METHODS = ["UPI", "CREDIT_CARD", "DEBIT_CARD", "WALLET", "COD"]


def delivery_callback(err, msg):
    """
    Kafka delivery report callback triggered once by poll() or flush()
    when a message has been successfully acknowledged by the broker
    or failed permanently.
    """
    if err is not None:
        print(f"[DELIVERY FAILED] Message delivery failed: {err}")
    else:
        # Message was successfully written to the partition commit log
        print(
            f"[ACK DELIVERED] Topic: {msg.topic()} | "
            f"Partition: {msg.partition()} | "
            f"Offset: {msg.offset()} | "
            f"Key: {msg.key().decode('utf-8')}"
        )


def generate_order_event() -> dict:
    """Generates a realistic order payload."""
    order_id = f"ORD-{random.randint(100000, 999999)}"
    customer_id = f"CUST-{random.randint(1000, 9999)}"
    dark_store_id = random.choice(DARK_STORES)
    delivery_partner_id = f"RIDER-{random.randint(100, 999)}"

    # Pick 1 to 4 distinct items
    chosen_items = random.sample(CATALOG, k=random.randint(1, 4))
    order_items = []
    total_amount = 0.0

    for item in chosen_items:
        qty = random.randint(1, 3)
        unit_price = item["price"]
        order_items.append({
            "product_id": item["product_id"],
            "product_name": item["name"],
            "category": item["category"],
            "quantity": qty,
            "unit_price_inr": unit_price,
        })
        total_amount += unit_price * qty

    total_amount = round(total_amount, 2)

    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "dark_store_id": dark_store_id,
        "delivery_partner_id": delivery_partner_id,
        "items": order_items,
        "total_amount_inr": total_amount,
        "payment_method": random.choice(PAYMENT_METHODS),
        "delivery_promise_min": 10,
        "is_zepto_pass": random.choice([True, False, False]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def produce_orders(num_orders: int = 10, delay_sec: float = 1.0):
    """
    Initializes Kafka Producer and sends order events.
    
    :param num_orders: Number of orders to generate (set to 0 for infinite loop)
    :param delay_sec: Seconds to wait between messages to simulate real-time traffic
    """
    print(f"[INFO] Initializing Kafka Producer connecting to {PRODUCER_CONFIG['bootstrap.servers']}...")
    producer = Producer(PRODUCER_CONFIG)

    count = 0
    try:
        while True:
            order = generate_order_event()
            order_id = order["order_id"]

            # Key concept: We use order_id as the message KEY.
            # Kafka hashes the key so all updates for this order go to the same partition!
            key_bytes = order_id.encode("utf-8")
            value_bytes = json.dumps(order).encode("utf-8")

            # Asynchronously send message to Kafka topic
            producer.produce(
                topic=TOPIC_ORDERS,
                key=key_bytes,
                value=value_bytes,
                on_delivery=delivery_callback,
            )

            # Serve delivery callback queue (non-blocking)
            producer.poll(0)

            count += 1
            print(f"[SENT] {order_id} | Total: Rs {order['total_amount_inr']} | Store: {order['dark_store_id']}")

            if num_orders > 0 and count >= num_orders:
                break

            time.sleep(delay_sec)

    except KeyboardInterrupt:
        print("\n[INFO] Producer interrupted by user.")
    finally:
        # Crucial: Wait for any outstanding messages to be delivered before shutting down
        print("[INFO] Flushing producer queue to ensure all messages are delivered...")
        remaining = producer.flush(timeout=10.0)
        if remaining > 0:
            print(f"[WARNING] {remaining} messages remained in queue.")
        else:
            print(f"[SUCCESS] Successfully produced and acknowledged {count} order events!")


if __name__ == "__main__":
    # By default, produce 5 orders with 0.5s pause to observe Kafka in action
    produce_orders(num_orders=5, delay_sec=0.5)
