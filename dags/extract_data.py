from airflow.decorators import dag, task
import urllib.request
import pendulum
import logging
import shutil
import gzip

logger = logging.getLogger(__name__)

url = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz"
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
}


@dag(
    dag_id="extract_data",
    default_args=default_args,
    description="Downloads and unzip the CSV file from the source.",
    schedule_interval="@once",
    catchup=False,
    max_active_runs=1,
    start_date=pendulum.datetime(2024, 1, 1),
)
def extract_data():

    @task
    def download_csv():
        logger.info("Downloading the data...")
        with urllib.request.urlopen(url) as response, open(
            "output.csv.gz", "wb"
        ) as out_file:
            shutil.copyfileobj(response, out_file)

    @task
    def extract_csv(task_id="extract_csv"):
        logger.info("Extracting the data...")
        with gzip.open("output.csv.gz", "rb") as f_in:
            with open("output.csv", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

    download_csv() >> extract_csv()


extract_data = extract_data()
