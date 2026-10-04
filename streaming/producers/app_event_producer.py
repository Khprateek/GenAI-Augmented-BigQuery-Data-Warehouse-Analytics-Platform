"""
App Clickstream Event Producer.

Simulates mobile app and web browser user sessions (browsing, search, cart, checkout).
Publishes events to topic: quickcommerce.app_events
"""

import json
import random
import time
import uuid
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
from streaming.config import PRODUCER_CONFIG, TOPIC_APP_EVENTS

SEARCH_TERMS = [
    "milk", "curd", "bread", "eggs", "potato",
    "onion", "tomato", "chips", "coke", "ice cream"
]

SCREENS = ["home_feed", "category_dairy", "search_results", "product_details", "cart_drawer", "checkout_screen"]


def delivery_callback(err, msg):
    if err is not None:
        print(f"[DELIVERY FAILED] Clickstream event failed: {err}")
    else:
        print(
            f"[ACK EVENT] Topic: {msg.topic()} | "
            f"Partition: {msg.partition()} | "
            f"Offset: {msg.offset()} | "
            f"Key: {msg.key().decode('utf-8')}"
        )


def simulate_user_session(producer: Producer, customer_id: str):
    """
    Simulates a sequence of user clickstream events for one app session.
    Key Concept: We use customer_id as the message KEY so that all events from the
    same user are routed to the same partition and preserve session chronology.
    """
    session_id = f"SESS-{uuid.uuid4().hex[:8]}"
    platform = random.choice(["android", "ios", "web"])

    funnel_steps = [
        ("page_view", "home_feed", None),
        ("search", "search_results", random.choice(SEARCH_TERMS)),
        ("product_view", "product_details", None),
        ("add_to_cart", "cart_drawer", None),
        ("checkout_start", "checkout_screen", None),
    ]

    # Randomly stop at different steps of funnel
    drop_point = random.randint(2, len(funnel_steps))

    print(f"\n--- User Session {session_id} for {customer_id} ({platform}) ---")

    for i in range(drop_point):
        event_type, screen, search_term = funnel_steps[i]

        payload = {
            "event_id": f"EVT-{uuid.uuid4().hex[:10]}",
            "customer_id": customer_id,
            "session_id": session_id,
            "event_type": event_type,
            "platform": platform,
            "page_or_screen": screen,
            "search_term": search_term,
            "product_id": f"PRD-{random.randint(100, 999)}" if "product" in event_type or "cart" in event_type else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        key_bytes = customer_id.encode("utf-8")
        value_bytes = json.dumps(payload).encode("utf-8")

        producer.produce(
            topic=TOPIC_APP_EVENTS,
            key=key_bytes,
            value=value_bytes,
            on_delivery=delivery_callback,
        )
        producer.poll(0)

        print(f"[CLICKSTREAM] {event_type} on {screen} {f'(Query: {search_term})' if search_term else ''}")
        time.sleep(0.2)


def produce_app_events(num_sessions: int = 3):
    print(f"[INFO] Initializing App Event Producer to {PRODUCER_CONFIG['bootstrap.servers']}...")
    producer = Producer(PRODUCER_CONFIG)

    try:
        for _ in range(num_sessions):
            customer_id = f"CUST-{random.randint(1000, 9999)}"
            simulate_user_session(producer, customer_id)
            time.sleep(0.4)

    except KeyboardInterrupt:
        print("\n[INFO] App event producer interrupted by user.")
    finally:
        print("\n[INFO] Flushing clickstream producer buffer...")
        producer.flush(timeout=10.0)
        print("[SUCCESS] All clickstream events flushed and acknowledged!")


if __name__ == "__main__":
    produce_app_events(num_sessions=3)
