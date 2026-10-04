"""
App Event & Real-Time Funnel Analytics Consumer.

Subscribes to topic: quickcommerce.app_events
Aggregates live clickstream events into conversion funnel metrics
(Page View -> Search -> Product View -> Add to Cart -> Checkout).
"""

import json
import sys
from pathlib import Path
from confluent_kafka import Consumer, KafkaError

# Ensure utf-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from streaming.config import (
    TOPIC_APP_EVENTS,
    GROUP_EVENT_ANALYZER,
    get_consumer_config,
)


def consume_app_events(max_messages: int = 0):
    conf = get_consumer_config(group_id=GROUP_EVENT_ANALYZER, auto_offset_reset="earliest")
    print(f"[INFO] Initializing Funnel Analytics Consumer with Group: '{conf['group.id']}'...")
    consumer = Consumer(conf)

    consumer.subscribe([TOPIC_APP_EVENTS])
    print(f"[INFO] Subscribed to topic: '{TOPIC_APP_EVENTS}'. Waiting for clickstream events...")

    # Real-time funnel counters
    funnel_counts = {
        "page_view": 0,
        "search": 0,
        "product_view": 0,
        "add_to_cart": 0,
        "checkout_start": 0,
    }

    platform_counts = {"android": 0, "ios": 0, "web": 0}
    top_searches = {}

    try:
        message_count = 0
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"[ERROR] Consumer error: {msg.error()}")
                    break

            event = json.loads(msg.value().decode("utf-8"))
            event_type = event.get("event_type")
            platform = event.get("platform", "web")
            cust_id = event.get("customer_id")
            screen = event.get("page_or_screen")
            search_term = event.get("search_term")

            message_count += 1

            if event_type in funnel_counts:
                funnel_counts[event_type] += 1
            if platform in platform_counts:
                platform_counts[platform] += 1
            if search_term:
                top_searches[search_term] = top_searches.get(search_term, 0) + 1

            print(
                f"[EVENT] {event_type:<15} | Platform: {platform:<7} | Screen: {screen:<18} "
                f"| Cust: {cust_id} | Partition: {msg.partition()}"
            )

            # Every 5 messages, display live funnel snapshot
            if message_count % 5 == 0:
                print("\n   📊 [Live Funnel Metrics]")
                for stage, cnt in funnel_counts.items():
                    print(f"      • {stage:<16}: {cnt}")
                print()

            if max_messages > 0 and message_count >= max_messages:
                print(f"\n[INFO] Reached requested limit of {max_messages} clickstream events.")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Funnel consumer stopped by user.")
    finally:
        consumer.close()
        print("\n================ FINAL FUNNEL REPORT ================")
        for stage, cnt in funnel_counts.items():
            print(f"  {stage:<16}: {cnt}")
        print(f"  Platforms: {platform_counts}")
        print("=====================================================")


if __name__ == "__main__":
    consume_app_events()
