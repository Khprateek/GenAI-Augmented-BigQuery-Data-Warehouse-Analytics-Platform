import os
import sys
import argparse
import logging
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# =====================================================
# Configuration
# =====================================================

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

RAW_DATASET = "raw"

# Categorized tables
DIMENSION_TABLES = [
    "customers",
    "dark_stores",
    "delivery_partners",
    "products",
    "marketing_spend",
]

FACT_TABLES = [
    "orders",
    "order_items",
    "order_issues",
    "events",
]

ALL_TABLES = DIMENSION_TABLES + FACT_TABLES

# Dedicated folder paths
BASE_DIR = Path(__file__).resolve().parent.parent
DIMENSIONS_DIR = BASE_DIR / "data" / "raw" / "dimensions"
FACTS_DIR = BASE_DIR / "data" / "raw" / "facts"
FALLBACK_RAW2_DIR = BASE_DIR / "data" / "raw2"

# =====================================================
# Logging
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("bigquery_loader")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

_client = None

def get_bigquery_client():
    global _client
    if _client is not None:
        return _client

    proj_id = os.getenv("GCP_PROJECT_ID")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not proj_id:
        raise ValueError("Environment variable GCP_PROJECT_ID is not set.")
    if not creds_path:
        raise ValueError("Environment variable GOOGLE_APPLICATION_CREDENTIALS is not set.")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Credentials file not found: {creds_path}")

    credentials = service_account.Credentials.from_service_account_file(creds_path)
    _client = bigquery.Client(project=proj_id, credentials=credentials)
    return _client

# =====================================================
# Helper Functions
# =====================================================

def resolve_csv_path(table_name: str) -> Path | None:
    """
    Resolves the CSV file path by checking dedicated dimension/fact folders,
    with fallback to legacy raw directories.
    """
    # 1. Check dimension folder if table is a dimension
    if table_name in DIMENSION_TABLES:
        p = DIMENSIONS_DIR / f"{table_name}.csv"
        if p.exists():
            return p

    # 2. Check facts folder if table is a fact
    if table_name in FACT_TABLES:
        p = FACTS_DIR / f"{table_name}.csv"
        if p.exists():
            return p

    # 3. Fallback checks
    dim_path = DIMENSIONS_DIR / f"{table_name}.csv"
    if dim_path.exists():
        return dim_path

    fact_path = FACTS_DIR / f"{table_name}.csv"
    if fact_path.exists():
        return fact_path

    raw2_path = FALLBACK_RAW2_DIR / f"{table_name}.csv"
    if raw2_path.exists():
        return raw2_path

    return None


def load_table(table_name: str) -> None:
    """
    Load a CSV file into BigQuery raw dataset.
    """
    csv_path = resolve_csv_path(table_name)

    if not csv_path or not csv_path.exists():
        logger.warning(f"File not found for table '{table_name}' in dimensions or facts directory")
        return

    logger.info(f"Reading {csv_path}")

    df = pd.read_csv(csv_path, encoding='utf-8', encoding_errors='replace')

    logger.info(
        f"{table_name}: {len(df):,} rows loaded from CSV"
    )

    client = get_bigquery_client()
    proj_id = os.getenv("GCP_PROJECT_ID")
    destination_table = (
        f"{proj_id}.{RAW_DATASET}.{table_name}"
    )

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True
    )

    load_job = client.load_table_from_dataframe(
        dataframe=df,
        destination=destination_table,
        job_config=job_config
    )

    load_job.result()

    table = client.get_table(destination_table)

    logger.info(
        f"{table_name}: "
        f"{table.num_rows:,} rows written to BigQuery"
    )


# =====================================================
# Main
# =====================================================

def main():
    parser = argparse.ArgumentParser(description="Load quick-commerce CSV data into BigQuery raw dataset.")
    parser.add_argument("--dimensions-only", action="store_true", help="Load only master/dimension tables")
    parser.add_argument("--facts-only", action="store_true", help="Load only transactional/fact tables")
    parser.add_argument("--table", type=str, help="Load a specific table only")

    args = parser.parse_args()

    if args.table:
        target_tables = [args.table]
    elif args.dimensions_only:
        target_tables = DIMENSION_TABLES
    elif args.facts_only:
        target_tables = FACT_TABLES
    else:
        target_tables = ALL_TABLES

    logger.info("=" * 60)
    logger.info(f"Starting BigQuery Load for {len(target_tables)} tables")
    logger.info(f"Tables: {', '.join(target_tables)}")
    logger.info("=" * 60)

    for table in target_tables:
        try:
            load_table(table)
        except Exception as e:
            logger.exception(f"Failed loading table {table}: {e}")

    logger.info("=" * 60)
    logger.info("BigQuery Load Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()