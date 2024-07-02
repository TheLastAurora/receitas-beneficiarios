from sqlalchemy import create_engine, text
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.models import Variable
from airflow.decorators import dag, task
from datetime import datetime
from time import time
import polars as pl
import logging

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
}


@dag(
    dag_id="dump_data",
    description="Dump the raw data into to the database.",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    catchup=False,
)
def dump_data():

    wait_data_preparation = ExternalTaskSensor(
        task_id="wait_data_preparation",
        external_dag_id="extract_data",
        external_task_id="extract_csv",
        check_existence=True,
        timeout=200,
    )

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
                batched_df.to_pandas().infer_objects().to_sql(
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

    wait_data_preparation >> insert_data()


dump_data = dump_data()
