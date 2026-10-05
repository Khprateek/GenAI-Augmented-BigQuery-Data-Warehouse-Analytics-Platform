"""
Order Items Event Producer (Scaffolding).

Produces line-item granular events to topic: quickcommerce.order_items
Matches schema contract for BigQuery raw.order_items table:
- order_item_id
- order_id
- product_id
- quantity
- unit_price
- is_substituted
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from streaming.config import PRODUCER_CONFIG, TOPIC_ORDER_ITEMS


def produce_order_items():
    """Placeholder: Will emit individual order line items to quickcommerce.order_items."""
    pass


if __name__ == "__main__":
    print("[INFO] Order items producer placeholder ready.")
