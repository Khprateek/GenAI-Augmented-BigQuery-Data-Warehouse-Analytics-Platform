from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "/opt/airflow/project"  # update to your path

default_args = {"owner":"airflow","retries":2,"retry_delay":timedelta(minutes=5)}

with DAG("ecommerce_ingestion", default_args=default_args, schedule_interval="@daily",
         start_date=datetime(2024,1,1), catchup=False, tags=["ecommerce","ingestion"]) as dag:

    generate = BashOperator(task_id="generate_data",
        bash_command=f"cd {PROJECT_ROOT}/data && python generate_data.py")

    load_raw = BashOperator(task_id="load_raw_to_bigquery",
        bash_command=f"cd {PROJECT_ROOT}/loaders && python load_to_bigquery.py")

    generate >> load_raw