"""
Order Issues Event Producer (Scaffolding).

Produces post-delivery order issue and resolution events to topic: quickcommerce.order_issues
Matches schema contract for BigQuery raw.order_issues table:
- issue_id
- order_id
- product_id
- reported_at
- issue_type
- resolution
- resolved_same_day
- refund_amount
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from streaming.config import PRODUCER_CONFIG, TOPIC_ORDER_ISSUES


def produce_order_issues():
    """Placeholder: Will emit order issue events to quickcommerce.order_issues."""
    pass


if __name__ == "__main__":
    print("[INFO] Order issues producer placeholder ready.")
