from sqlalchemy import create_engine, text
from airflow.decorators import dag, task
from airflow.models import Variable
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
}


@dag(
    dag_id="connect_db",
    description="Connects the Airflow instance to the database.",
    start_date=datetime(2024, 6, 24),
    default_args=default_args,
    schedule_interval='@once',
    catchup=False,
)
def connect_db():

    @task
    def set_env_vars():
        env_vars = {
            "DB_USER": os.environ["POSTGRES_USER"],
            "DB_PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "DB_HOST": os.environ["DB_HOST"],
            "DB_NAME": os.environ["POSTGRES_DB"],
            "INGESTION_BATCH_SIZE": os.environ["BATCH_SIZE"],
            "RAW_TBL_NAME": os.environ["TABLE_NAME"],
        }
        for k, v in env_vars.items():
            Variable.set(k, v)
            logger.info(f"{k} airflow env set.")

    @task()
    def db_conn():
        url = "postgresql+psycopg2://{user}:{password}@{host}:5432/{db}".format(
            user=Variable.get("DB_USER"),
            password=Variable.get("DB_PASSWORD"),
            host=Variable.get("DB_HOST"),
            db=Variable.get("DB_NAME"),
        )
        engine = create_engine(url)
        conn = engine.connect()
        try:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection successfully stablished.")
            Variable.set("DB_URL", value=url)  # Not the best way.
        except Exception as e:
            logger.error(f"Couldn't stablish database connection: {e}")

    set_env_vars() >> db_conn()


connect = connect_db()
