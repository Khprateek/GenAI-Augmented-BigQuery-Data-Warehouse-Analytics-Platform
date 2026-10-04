"""
Order Event Consumer for Quick-Commerce Platform.

Reads real-time orders from Kafka topic: quickcommerce.orders
Processes each order, tracks running KPIs (Total Revenue, Order Count, Store Breakdown),
and demonstrates consumer group offset management.
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
    TOPIC_ORDERS,
    GROUP_ORDER_PROCESSOR,
    get_consumer_config,
)


def consume_orders(max_messages: int = 0):
    """
    Subscribes to quickcommerce.orders and processes incoming messages.
    
    :param max_messages: Maximum messages to consume before stopping (0 for infinite loop)
    """
    # Create consumer config with our dedicated consumer group
    conf = get_consumer_config(group_id=GROUP_ORDER_PROCESSOR, auto_offset_reset="earliest")
    print(f"[INFO] Initializing Consumer with Group: '{conf['group.id']}'...")
    consumer = Consumer(conf)

    # Subscribe to topic(s)
    consumer.subscribe([TOPIC_ORDERS])
    print(f"[INFO] Subscribed to topic: '{TOPIC_ORDERS}'. Waiting for messages (Press Ctrl+C to stop)...")

    # In-memory running analytics
    total_orders = 0
    total_revenue_inr = 0.0
    store_orders = {}

    try:
        while True:
            # Poll Kafka for messages. Timeout in seconds.
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                # No new message within 1.0s timeout
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event (not an error)
                    continue
                else:
                    print(f"[ERROR] Consumer error: {msg.error()}")
                    break

            # Deserialize Kafka record
            raw_key = msg.key().decode("utf-8") if msg.key() else "NoKey"
            order_data = json.loads(msg.value().decode("utf-8"))

            order_id = order_data["order_id"]
            amount = order_data["total_amount_inr"]
            store = order_data["dark_store_id"]
            items_count = len(order_data.get("items", []))

            # Update running metrics
            total_orders += 1
            total_revenue_inr += amount
            store_orders[store] = store_orders.get(store, 0) + 1

            # Print event consumption details
            print(
                f"[ORDER RECEIVED] Partition: {msg.partition()} | Offset: {msg.offset()} | "
                f"ID: {order_id} | Amount: Rs {amount:,.2f} | Items: {items_count} | Store: {store}"
            )
            print(
                f"   ↳ [Running Totals] Orders: {total_orders} | "
                f"Cumulative Revenue: Rs {total_revenue_inr:,.2f}"
            )

            if max_messages > 0 and total_orders >= max_messages:
                print(f"\n[INFO] Reached requested limit of {max_messages} messages.")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Consumer stopped by user.")
    finally:
        # Crucial: Close consumer to commit final offsets and gracefully leave the group
        print("[INFO] Closing consumer and committing offsets...")
        consumer.close()
        print(f"[SUMMARY] Processed {total_orders} total orders. Revenue: Rs {total_revenue_inr:,.2f}")


if __name__ == "__main__":
    # By default, read existing messages from beginning
    consume_orders()
