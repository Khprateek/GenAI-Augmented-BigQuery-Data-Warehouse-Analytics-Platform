"""
Order Status Lifecycle Event Producer.

Simulates the real-time fulfillment progression of quick-commerce orders:
ORDER_PLACED -> DARK_STORE_PACKING -> RIDER_ASSIGNED -> OUT_FOR_DELIVERY -> DELIVERED
Publishes to topic: quickcommerce.order_status
"""

import json
import random
import time
import sys
from pathlib import Path
from datetime import datetime, timezone
from confluent_kafka import Producer

# Ensure utf-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from streaming.config import PRODUCER_CONFIG, TOPIC_ORDER_STATUS

STATUS_FLOW = [
    ("ORDER_PLACED", 0, "Order accepted by system and dispatched to dark store queue"),
    ("DARK_STORE_PACKING", 90, "Store executive picking items from racks into delivery bag"),
    ("RIDER_ASSIGNED", 180, "Delivery partner assigned at dark store dock"),
    ("OUT_FOR_DELIVERY", 300, "Rider departed dark store on 10-minute delivery route"),
    ("DELIVERED", 540, "Order successfully delivered to customer doorstep"),
]


def delivery_callback(err, msg):
    if err is not None:
        print(f"[DELIVERY FAILED] Status update failed: {err}")
    else:
        print(
            f"[ACK STATUS] Topic: {msg.topic()} | "
            f"Partition: {msg.partition()} | "
            f"Offset: {msg.offset()} | "
            f"Key: {msg.key().decode('utf-8')}"
        )


def simulate_order_lifecycle(producer: Producer, order_id: str, fast_mode: bool = True):
    """
    Emits the entire chronological status progression for a specific order.
    
    CRUCIAL KAFKA CONCEPT:
    Because we use order_id as the message KEY for every single status update,
    Kafka's hashing ensures that ALL status transitions for this order land in the
    SAME partition in strict chronological order!
    """
    customer_id = f"CUST-{random.randint(1000, 9999)}"
    dark_store_id = f"DS-BLR-{random.choice(['KORAMANGALA', 'INDIRANAGAR', 'HSR'])}"
    rider_id = f"RIDER-{random.randint(100, 999)}"

    # 95% of orders succeed, 5% cancelled early
    is_cancelled = random.random() < 0.05

    print(f"\n--- Simulating Lifecycle for {order_id} ---")

    for status, elapsed_sec, notes in STATUS_FLOW:
        if is_cancelled and status == "RIDER_ASSIGNED":
            status = "CANCELLED"
            notes = "Customer cancelled order before rider dispatch"

        status_event = {
            "order_id": order_id,
            "customer_id": customer_id,
            "dark_store_id": dark_store_id,
            "delivery_partner_id": rider_id,
            "status": status,
            "elapsed_time_sec": elapsed_sec,
            "notes": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        key_bytes = order_id.encode("utf-8")
        value_bytes = json.dumps(status_event).encode("utf-8")

        producer.produce(
            topic=TOPIC_ORDER_STATUS,
            key=key_bytes,
            value=value_bytes,
            on_delivery=delivery_callback,
        )
        producer.poll(0)

        print(f"[STATUS] {order_id} -> {status} (+{elapsed_sec}s) | {notes}")

        if status == "CANCELLED":
            break

        # Simulate delay between transitions (e.g. 0.3s in fast simulation)
        time.sleep(0.3 if fast_mode else 1.5)


def produce_status_events(num_orders: int = 3):
    print(f"[INFO] Initializing Order Status Producer to {PRODUCER_CONFIG['bootstrap.servers']}...")
    producer = Producer(PRODUCER_CONFIG)

    try:
        for i in range(num_orders):
            order_id = f"ORD-{random.randint(200000, 899999)}"
            simulate_order_lifecycle(producer, order_id)
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[INFO] Status producer stopped by user.")
    finally:
        print("\n[INFO] Flushing producer buffer...")
        producer.flush(timeout=10.0)
        print("[SUCCESS] All order status events flushed and acknowledged!")


if __name__ == "__main__":
    produce_status_events(num_orders=3)
