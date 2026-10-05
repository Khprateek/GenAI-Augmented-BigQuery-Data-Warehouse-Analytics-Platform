"""
Master Data Orchestrator for Quick-Commerce Platform.

Executes both dimension and fact generators in sequence:
  1. generate_dimensions.py -> data/raw/dimensions/ (stores, riders, customers, products, marketing)
  2. generate_facts.py      -> data/raw/facts/      (orders, items, issues, clickstream)

Run:
  python data/generate_data.py            # Generates both dimensions and facts
  python data/generate_dimensions.py      # Generates master/dimension data only
  python data/generate_facts.py           # Generates transactional/fact data only
"""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from generate_dimensions import generate_dimensions
from generate_facts import generate_facts


def main():
    print("=" * 70)
    print("🚀 QUICK-COMMERCE END-TO-END DATA GENERATION PIPELINE")
    print("=" * 70)

    # Step 1: Master / Dimension Tables
    generate_dimensions()
    print()

    # Step 2: Transactional / Fact Tables
    generate_facts()
    print()

    print("=" * 70)
    print("🎉 ALL DATA GENERATION TASKS COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()