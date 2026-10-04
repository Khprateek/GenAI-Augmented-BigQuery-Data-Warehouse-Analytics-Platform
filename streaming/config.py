"""
Central configuration for Kafka streaming pipelines.
Provides broker connections, topic definitions, and reusable client settings.
"""

import os

# --- Kafka Broker Configuration ---
# When running python scripts on your host machine (Windows), connect to localhost:9092.
# If running inside Docker, connect to kafka:29092.
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# --- Topic Definitions ---
TOPIC_ORDERS = "quickcommerce.orders"
TOPIC_ORDER_STATUS = "quickcommerce.order_status"
TOPIC_APP_EVENTS = "quickcommerce.app_events"

ALL_TOPICS = [
    TOPIC_ORDERS,
    TOPIC_ORDER_STATUS,
    TOPIC_APP_EVENTS,
]

# --- Consumer Group Definitions ---
# Each distinct business workflow has its own Consumer Group ID
# so they can read the same stream independently without interfering.
GROUP_ORDER_PROCESSOR = "order-processing-group"
GROUP_STATUS_TRACKER = "order-status-tracker-group"
GROUP_EVENT_ANALYZER = "app-event-analytics-group"

# --- Common Producer Configuration ---
PRODUCER_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "client.id": "quickcommerce-producer",
    # 'acks': 'all' ensures highest durability (leader and replicas must acknowledge)
    "acks": "all",
    # Retry on transient network errors
    "retries": 3,
    # Batching to optimize network throughput (in bytes)
    "batch.size": 16384,
    # Wait up to 10ms to fill the batch buffer before sending
    "linger.ms": 10,
}

# --- Base Consumer Configuration Template ---
def get_consumer_config(group_id: str, auto_offset_reset: str = "earliest") -> dict:
    """
    Returns consumer configuration dictionary for confluent-kafka.
    
    :param group_id: Unique consumer group name.
    :param auto_offset_reset: Where to start reading if no committed offset is found:
                              'earliest' (from beginning) or 'latest' (only new events).
    """
    return {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": group_id,
        "auto.offset.reset": auto_offset_reset,
        # Periodically commit consumed offsets in background
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 5000,
    }
