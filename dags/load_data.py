from sqlalchemy import create_engine, text
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.sensors.external_task import ExternalTaskSensor
from datetime import datetime
import logging
import os
import urllib.request
import shutil
import gzip
import polars as pl
from time import time

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
}


@dag(
    dag_id="load_data",
    description="Loads CSV data to the database by connecting to DB, downloading and extracting the data, and dumping it into the database.",
    start_date=datetime(2024, 6, 24),
    default_args=default_args,
    schedule_interval="@once",
    catchup=False,
)
def load_data():

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
            Variable.set("DB_URL", value=url)  # Not the best way, since it exposes the db pwd.
        except Exception as e:
            logger.error(f"Couldn't stablish database connection: {e}")

    @task
    def download_csv():
        url = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz"
        logger.info("Downloading the data...")
        with urllib.request.urlopen(url) as response, open(
            "output.csv.gz", "wb"
        ) as out_file:
            shutil.copyfileobj(response, out_file)

    @task
    def extract_csv():
        logger.info("Extracting the data...")
        with gzip.open("output.csv.gz", "rb") as f_in:
            with open("output.csv", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

    @task
    def insert_data():
        engine = create_engine(Variable.get("DB_URL"))
        with engine.connect() as conn:
            logger.info(f"Connected to database.")
            conn.execute(text(f"DROP TABLE IF EXISTS {Variable.get('RAW_TBL_NAME')}"))
            offset = 0
            stop = False
            logger.info("Starting ingestion...")
            t0_start = time()
            while True:
                t_start = time()
                try:
                    batched_df = pl.read_csv(
                        "output.csv",
                        n_rows=int(Variable.get("INGESTION_BATCH_SIZE")),
                        skip_rows_after_header=offset,
                        infer_schema_length=0,
                    )
                except:
                    batched_df = pl.read_csv(
                        "output.csv",
                        skip_rows_after_header=offset
                        - int(Variable.get("INGESTION_BATCH_SIZE")),
                        infer_schema_length=0,
                    )
                    stop = True
                batched_df = batched_df.to_pandas().convert_dtypes()
                print(batched_df.dtypes)
                batched_df.to_sql(
                    name=Variable.get("RAW_TBL_NAME"),
                    if_exists="append",
                    con=conn,
                    index=False,
                )
                t_end = time()
                logging.info(
                    f"Inserted batch starting at row {offset} in {t_end - t_start:.3f} seconds"
                )
                if stop:
                    break
                offset += int(Variable.get("INGESTION_BATCH_SIZE"))

            logger.info(f"Insertion completed in {time() - t0_start:.3f} seconds")

    set_env_vars_task = set_env_vars()
    db_conn_task = db_conn()
    download_csv_task = download_csv()
    extract_csv_task = extract_csv()
    insert_data_task = insert_data()

    (
        set_env_vars_task
        >> db_conn_task
        >> download_csv_task
        >> extract_csv_task
        >> insert_data_task
    )


load_data = load_data()
