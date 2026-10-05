"""
Order Items Consumer (Scaffolding).

Reads line-item granular events from topic: quickcommerce.order_items
Processes order line items and streams them directly to BigQuery raw.order_items
or running product sales aggregates.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from streaming.config import TOPIC_ORDER_ITEMS, GROUP_ORDER_ITEMS_PROCESSOR, get_consumer_config


def consume_order_items():
    """Placeholder: Will consume order items from quickcommerce.order_items."""
    pass


if __name__ == "__main__":
    print("[INFO] Order items consumer placeholder ready.")
