from sqlalchemy import create_engine, text
from airflow.decorators import dag, task
import logging
import os
import polars as pl
import pendulum

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
}

@dag(
    dag_id="partition",
    description="Partitions de table by date",
    start_date=pendulum.datetime(2024, 6, 24),
    default_args=default_args,
    schedule_interval="@once",
    catchup=False,
)
def partition_data():
    pass