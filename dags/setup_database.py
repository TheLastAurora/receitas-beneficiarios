from airflow.decorators import dag, task, task_group
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from sqlalchemy import create_engine, text
from airflow.models import Variable
import pendulum
import logging
import os

logger = logging.getLogger(__name__)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
}

TABLE_NAME = os.environ["TABLE_NAME"]

@dag(
    dag_id="setup_database",
    default_args=default_args,
    description="Creates the database tables, its partitions, indexes and triggers.",
    catchup=False,
    # schedule="@once",  # Use this if you wish to execute the full pipeline automatically.
    max_active_runs=1,
    start_date=pendulum.now(),
    concurrency=40
)
def setup():

    DROP_QUERY = f"DROP TABLE IF EXISTS {TABLE_NAME}"
    CREATE_QUERY = f"""
        CREATE TABLE {TABLE_NAME} (
            id SERIAL,
            codigo_favorecido VARCHAR(255),
            nome_favorecido VARCHAR(255),
            sigla_uf VARCHAR(255),
            nome_municipio VARCHAR(255),
            codigo_orgao_superior BIGINT,
            nome_orgao_superior VARCHAR(255),
            codigo_orgao BIGINT,
            nome_orgao VARCHAR(255),
            codigo_unidade_gestora BIGINT,
            nome_unidade_gestora VARCHAR(255),
            ano_e_mes_do_lancamento DATE,
            valor_recebido FLOAT,
            PRIMARY KEY (id, ano_e_mes_do_lancamento)
        ) PARTITION BY RANGE(ano_e_mes_do_lancamento);
    """

    CREATE_PARTITIONS_TEMPLATE = f"""
        CREATE TABLE {TABLE_NAME}_{{month}}_{{year}} PARTITION OF {TABLE_NAME}
        FOR VALUES FROM ('{{start_date}}') TO ('{{end_date}}');
    """

    CONSTRAINT_PARTITIONS_TEMPLATE = f"""
        ALTER TABLE {TABLE_NAME}_{{month}}_{{year}} ADD CONSTRAINT {TABLE_NAME}_{{month}}_{{year}}_check
        CHECK (ano_e_mes_do_lancamento >= '{{start_date}}' AND ano_e_mes_do_lancamento < '{{end_date}}');
    """

    INITIAL_DATE = pendulum.Date(2014, 1, 1)
    LATEST_DATE = pendulum.now(tz="America/Sao_Paulo").date()

    date_range = pendulum.interval(INITIAL_DATE, LATEST_DATE)
    dates_list = [dt.format("Y-MM-DD") for dt in date_range.range("months")]
    dates = list(zip(dates_list, dates_list[1:]))

    @task
    def set_env():
        env_vars = {
            "DB_USER": os.environ["POSTGRES_USER"],
            "DB_PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "DB_HOST": os.environ["DB_HOST"],
            "DB_NAME": os.environ["POSTGRES_DB"],
            "INGESTION_BATCH_SIZE": os.environ["BATCH_SIZE"],
            "TABLE_NAME": os.environ["TABLE_NAME"],
        }
        for k, v in env_vars.items():
            Variable.set(k, v)
            logger.info(f"Airflow {k} env variable set.")

    @task(task_id="push_dates")
    def push_dates(**context):
        _dates_list = [dt.format("YMM") for dt in date_range.range("months")]
        context['ti'].xcom_push(key='dates', value=_dates_list)
        return _dates_list

    @task
    def test_conn():
        url = f"postgresql+psycopg2://{Variable.get('DB_USER')}:{Variable.get('DB_PASSWORD')}@{Variable.get('DB_HOST')}:5432/{Variable.get('DB_NAME')}"
        engine = create_engine(url)
        try:
            conn = engine.connect()
            conn.execute(text("SELECT 1"))
            conn.close()
            logger.info("Database connection successfully established.")
            Variable.set("DB_URL", value=url)
        except Exception as e:
            logger.error(f"Couldn't establish database connection: {e}")
            raise

    @task_group()
    def setup_tbls(dates):
        
        @task
        def create_tbl():
            engine = create_engine(Variable.get("DB_URL"))
            with engine.connect() as conn:
                logger.info("Connected to database.")
                conn.execute(text(DROP_QUERY))
                conn.execute(text(CREATE_QUERY))
                logger.info(f"Table {TABLE_NAME} created")

        def setup_partitions(start_date, end_date):

            @task
            def create_partition(start_date, end_date):
                engine = create_engine(Variable.get("DB_URL"))
                with engine.connect() as conn:
                    conn.execute(
                        text(
                            CREATE_PARTITIONS_TEMPLATE.format(
                                month=start_date.split("-")[1],
                                year=start_date.split("-")[0],
                                start_date=start_date,
                                end_date=end_date,
                            )
                        )
                    )
                    logger.info(f"Partition {TABLE_NAME}_{start_date.split("-")[1]}_{start_date.split("-")[0]} created.")

            @task
            def constraint_partition(start_date, end_date):
                engine = create_engine(Variable.get("DB_URL"))
                with engine.connect() as conn:
                    conn.execute(
                        text(
                            CONSTRAINT_PARTITIONS_TEMPLATE.format(
                                month=start_date.split("-")[1],
                                year=start_date.split("-")[0],
                                start_date=start_date,
                                end_date=end_date,
                            )
                        )
                    )
                    logger.info(f"CHECK constraint added for partition {TABLE_NAME}_{start_date.split("-")[1]}_{start_date.split("-")[0]}.")

            create_partition(start_date, end_date) >> constraint_partition(start_date, end_date)

        create_tbl_task = create_tbl()

        for i, (start_date, end_date) in enumerate(dates):
            partitions_task_group = task_group(group_id=f"setup_partitions_{i}")(setup_partitions)(start_date, end_date)
            partitions_task_group.set_upstream(create_tbl_task)

    setup_trigger_load = TriggerDagRunOperator(
        task_id="completed",
        trigger_dag_id="load_data",
        execution_date="{{ ds }}",
        conf={"dates": "{{ ti.xcom_pull(task_ids='push_dates') }}"},
        reset_dag_run=True
    )
        
    set_env() >> test_conn() >> setup_tbls(dates) >> push_dates() >> setup_trigger_load

setup()
