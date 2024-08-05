# **Receipt of Resources by Beneficiary**

## **Features**

This project involves a ETL pipeline related to Receipt of Resources by Beneficiary from the [Transparency Portal](https://portaldatransparencia.gov.br/download-de-dados/despesas-favorecidos) using and open-source stack, such as Airflow, Kafka and Polars. It has an educational purpose only.

In the Airflow side, currently, the pipeline is structured into two primary DAGs (Directed Acyclic Graphs):

1. **`setup_pipeline` DAG**:
   - **Purpose**: Creates database tables, partitions, constraints, and sets up a Debezium connector for CDC.
   - **Tasks**:
     - Set environment variables.
     - Test database connection.
     - Create the main table and its partitions.
     - Set up constraints on the partitions.
     - Configure the Debezium connector.
     - Trigger the `load_data` DAG after setup completion.

2. **`load_data` DAG**:
   - **Purpose**: Downloads data files, processes CSV data, and inserts it into the database.
   - **Tasks**:
     - Pull dates from the configuration.
     - Download and save CSV files from a URL.
     - Process and insert data into the database using Polars for efficient CSV handling.
     - Handle batching and error management during data insertion.

## **Technologies Used**

- **Apache Airflow**: Orchestrating and managing the data pipeline.
- **Apache Spark**: Data processing [ONLY IN PROTOTYPE]
- **Docker**: Containerizing the Airflow setup and ensuring consistent execution environments.
- **Polars**: CSV file processing.
- **PostgreSQL**: Database management. 
- **Kafka**: Message streaming
- **Schema Registry**: Managing the Data schema versioning

## **Prerequisites**

1. **Git**: Ensure Git is installed on your machine. You can download it from the [official Git website](https://git-scm.com/downloads).

2. **Python**: Make sure Python is installed. Follow the instructions for installation from the [official Python website](https://www.python.org/downloads/).

3. **Docker**: Install Docker by following the instructions on the [official Docker website](https://docs.docker.com/get-docker/). Also, don't forget to [add the airflow user to the docker permissions](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html#setting-the-right-airflow-user).

4. **Docker Compose**: Install Docker Compose using the instructions [here](https://docs.docker.com/compose/install/).

## **Setup Instructions**

1. **Install Docker and Docker Compose**:
   - Follow the installation instructions for Docker from the [official Docker website](https://docs.docker.com/get-docker/).
   - Install Docker Compose using the instructions [here](https://docs.docker.com/compose/install/).

2. **Clone the Repository and set permissions (if necessary)**:

   ```sh
   git clone https://github.com/TheLastAurora/receitas-beneficiarios.git
   cd receitas-beneficiarios
   chmod 777 -R ./*
   ```

3. **Create and Activate a Virtual Environment**:

   **For Unix/macOS**:
   
     ```sh
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   **For Windows**:

     ```sh
     python -m venv .venv
     .venv\Scripts\activate
     ```

4. **Install Dependencies**:

   ```sh
   pip install -r requirements.txt
   ```

5. **Setup Environment Variables**:

   Ensure the following environment variables are set in your `.env` file as in the `.env_sample`:

      - `POSTGRES_USER`
      - `POSTGRES_PASSWORD`
      - `POSTGRES_DB`
      - `DB_HOST`
      - `TABLE_NAME`
      - `BATCH_SIZE`
      - `AIRFLOW_UID`

6. **Build and Run Docker Containers**:

   ```sh
   docker-compose up --build
   ```



7. **Access Airflow Web Interface**:
   - Open your web browser and navigate to `http://localhost:8081` to access the Airflow UI.
   - Trigger the `setup_pipeline` DAG manually from the Airflow UI if it does not start automatically.]
   - Monitor the execution of the `setup_pipeline` and `load_data` DAGs through the Airflow UI.
   - Check logs for debugging and verification.
   - Currently, you might have to check the first insert task in `load_data` as success to proceed with the pipeline (date bug/problem).

8. **Access Kafka-UI Web Interface**:
   - You can check the Kafka info on topics, messages and the schema registry in `http://localhost:8088`.

9. **Access Spark Web Interface**:
   - You are able to check the health of the spark clusters in `http://localhost:8085`.


## **Uninstall Instructions**

**Stop and Remove Docker Containers and Volumes**:

   ```sh
   docker-compose down --volumes --remove-orphans
   ```

## **Notes**

- Ensure that your PostgreSQL instance is properly configured and accessible from the Docker containers.
- Adjust batch sizes and concurrency settings based on your hardware capabilities and data volume to optimize performance.
- Also, Be aware that this will consume lots of ram and CPU.