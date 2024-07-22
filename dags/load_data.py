from airflow.decorators import dag, task, task_group
from sqlalchemy import create_engine
from airflow.models import Variable
from airflow.models import TaskInstance
from time import time
import polars as pl
import unicodedata
import pendulum
import requests
import logging
import zipfile
import ast
import io
import os

logger = logging.getLogger(__name__)

URL = "https://portaldatransparencia.gov.br/download-de-dados/despesas-favorecidos/{file_date}"
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
}


@dag(
    dag_id="load_data",
    default_args=default_args,
    description="Downloads data from source and loads CSV into memory, then dumps it to the database.",
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    start_date=pendulum.yesterday(),
    render_template_as_native_obj=True,
    concurrency=2,  # Keep in mind that you should balance the batch_size and the number of tasks you should execute. Also, if you increase this value by much, airflow might SIGTERM the task for running for too long or by of memory usage (-9 code).
)
def load_data():

    @task
    def pull_dates(**context):
        str_dates = context["dag_run"].conf.get("dates")
        return ast.literal_eval(str_dates)

    @task
    def get_file(file_id):
        try:
            response = requests.get(URL.format(file_date=file_id), stream=True)
            response.raise_for_status()
            zip_data = zipfile.ZipFile(io.BytesIO(response.content))
            csv = zip_data.namelist()[0]
            tmp_file_path = f"/tmp/{file_id}.csv"
            with open(tmp_file_path, "wb") as tmp_file:
                tmp_file.write(zip_data.open(csv).read())
            return tmp_file_path
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting file {file_id}: {e}")
            raise

    @task
    def insert_data(file_path):
        engine = create_engine(Variable.get("DB_URL"))
        batch_size = int(Variable.get("INGESTION_BATCH_SIZE", 10000))

        dtypes = {
            "codigo_favorecido": pl.Utf8,
            "nome_favorecido": pl.Utf8,
            "sigla_uf": pl.Utf8,
            "nome_municipio": pl.Utf8,
            "codigo_orgao_superior": pl.Int64,
            "nome_orgao_superior": pl.Utf8,
            "codigo_orgao": pl.Int64,
            "nome_orgao": pl.Utf8,
            "codigo_unidade_gestora": pl.Int64,
            "nome_unidade_gestora": pl.Utf8,
            "ano_e_mes_do_lancamento": pl.Date,
            "valor_recebido": pl.Utf8,
        }

        offset = 0
        stop = False
        with engine.connect() as conn:
            logger.info(
                f"Connected to database. Ready to insert file for: {file_path.split(os.path.sep)[-1]}"
            )
            t0_start = time()
            logger.info("Starting ingestion...")
            while True:
                t_start = time()
                try:
                    batched_df = pl.read_csv(
                        file_path,
                        n_rows=batch_size,
                        skip_rows_after_header=offset,
                        separator=";",
                        encoding="1252",
                        decimal_comma=True,
                        dtypes=dtypes,
                    )
                except:
                    batched_df = pl.read_csv(
                        file_path,
                        skip_rows_after_header=offset - batch_size,
                        separator=";",
                        encoding="1252",
                        decimal_comma=True,
                        dtypes=dtypes,
                    )
                    stop = True
                batched_df.columns = [
                    unicodedata.normalize("NFD", col.lower().replace(" ", "_"))
                    .encode("ascii", "ignore")
                    .decode("utf-8")
                    for col in batched_df.columns
                ]
                batched_df = batched_df.with_columns(
                    pl.col("ano_e_mes_do_lancamento").str.strptime(pl.Date, "%m/%Y")
                )
                batched_df.to_pandas().to_sql(
                    name=Variable.get("TABLE_NAME"),
                    if_exists="append",
                    con=conn,
                    index=False,
                )
                t_end = time()
                logger.info(
                    f"Inserted batch starting at row {offset} in {t_end - t_start:.3f} seconds"
                )
                if stop:
                    break
                offset += batch_size

            os.remove(file_path)
            logger.info(f"Insertion completed in {time() - t0_start:.3f} seconds")

    @task_group
    def process_insertion(dates):
        file_paths = get_file.expand(file_id=dates)
        insert_tasks = insert_data.expand(file_path=file_paths)

    dates = pull_dates()
    process_insertion(dates)


load_data()
