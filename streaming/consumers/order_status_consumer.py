"""
Order Status & SLA Tracking Consumer.

Subscribes to topic: quickcommerce.order_status
Monitors delivery fulfillment lifecycle, verifies 10-minute delivery SLAs,
and tracks delivery partner handoffs.
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
    TOPIC_ORDER_STATUS,
    GROUP_STATUS_TRACKER,
    get_consumer_config,
)


def consume_order_status(max_messages: int = 0):
    """
    Subscribes to quickcommerce.order_status to track order lifecycles and SLAs.
    """
    conf = get_consumer_config(group_id=GROUP_STATUS_TRACKER, auto_offset_reset="earliest")
    print(f"[INFO] Initializing SLA Consumer with Group: '{conf['group.id']}'...")
    consumer = Consumer(conf)

    consumer.subscribe([TOPIC_ORDER_STATUS])
    print(f"[INFO] Subscribed to topic: '{TOPIC_ORDER_STATUS}'. Waiting for lifecycle updates...")

    delivered_count = 0
    cancelled_count = 0
    total_delivered_sec = 0

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
            order_id = event["order_id"]
            status = event["status"]
            elapsed = event.get("elapsed_time_sec", 0)
            rider = event.get("delivery_partner_id", "Unassigned")
            message_count += 1

            if status == "DELIVERED":
                delivered_count += 1
                total_delivered_sec += elapsed
                mins = elapsed // 60
                secs = elapsed % 60
                sla_status = "ON-TIME (<= 10m)" if elapsed <= 600 else "DELAYED (> 10m)"
                print(
                    f"[DELIVERY SUCCESS] {order_id} delivered by {rider} in {mins}m {secs}s "
                    f"[{sla_status}] | Partition: {msg.partition()} Offset: {msg.offset()}"
                )
            elif status == "CANCELLED":
                cancelled_count += 1
                print(f"[ALERT CANCELLED] {order_id} was CANCELLED! Reason: {event.get('notes')}")
            else:
                print(
                    f"[IN-PROGRESS] {order_id} -> {status} (T+{elapsed}s) "
                    f"| Partition: {msg.partition()} Offset: {msg.offset()}"
                )

            if max_messages > 0 and message_count >= max_messages:
                print(f"\n[INFO] Reached requested limit of {max_messages} status updates.")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Status consumer stopped by user.")
    finally:
        consumer.close()
        avg_time = (total_delivered_sec / delivered_count) if delivered_count > 0 else 0
        print(f"\n[SUMMARY] Delivered: {delivered_count} | Cancelled: {cancelled_count} | Avg Delivery Time: {avg_time/60:.1f} mins")


if __name__ == "__main__":
    consume_order_status()
