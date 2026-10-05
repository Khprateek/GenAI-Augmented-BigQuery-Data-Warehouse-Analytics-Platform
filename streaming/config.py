"""
Central configuration for Kafka streaming pipelines.
Provides broker connections, topic definitions, and reusable client settings.
"""

import os

# --- Kafka Broker Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# --- Topic Definitions ---
TOPIC_ORDERS = "quickcommerce.orders"
TOPIC_ORDER_ITEMS = "quickcommerce.order_items"
TOPIC_ORDER_STATUS = "quickcommerce.order_status"
TOPIC_ORDER_ISSUES = "quickcommerce.order_issues"
TOPIC_APP_EVENTS = "quickcommerce.app_events"

ALL_TOPICS = [
    TOPIC_ORDERS,
    TOPIC_ORDER_ITEMS,
    TOPIC_ORDER_STATUS,
    TOPIC_ORDER_ISSUES,
    TOPIC_APP_EVENTS,
]

# --- Consumer Group Definitions ---
GROUP_ORDER_PROCESSOR = "order-processing-group"
GROUP_ORDER_ITEMS_PROCESSOR = "order-items-processing-group"
GROUP_STATUS_TRACKER = "order-status-tracker-group"
GROUP_ORDER_ISSUES_PROCESSOR = "order-issues-processing-group"
GROUP_EVENT_ANALYZER = "app-event-analytics-group"

# --- Common Producer Configuration ---
PRODUCER_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "client.id": "quickcommerce-producer",
    "acks": "all",
    "retries": 3,
    "batch.size": 16384,
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
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 5000,
    }
