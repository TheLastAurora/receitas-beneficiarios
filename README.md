Here's a comprehensive documentation for your project, covering features, technologies used, concurrency, distribution, and setup instructions:

---

# **Receipt of Resources by Beneficiary**

## **Features**

This project involves a data pipeline for extracting and loading data related to Receipt of Resources by Beneficiary from the [Transparency Portal](https://portaldatransparencia.gov.br/download-de-dados/despesas-favorecidos). This will be further extended as a full end-to-end DE project. It mainly uses Apache Airflow, Docker and PostgreSQL. The pipeline is structured into two primary DAGs (Directed Acyclic Graphs):

1. **`setup_database` DAG**:
   - **Purpose**: Creates database tables, partitions, and constraints.
   - **Tasks**:
     - Set environment variables.
     - Test database connection.
     - Create the main table and its partitions.
     - Set up constraints on the partitions.
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
- **Docker**: Containerizing the Airflow setup and ensuring consistent execution environments.
- **Polars**: CSV file processing.
- **PostgreSQL**: Database management.
- **SQLAlchemy**: Database connections and queries.
- **Requests**: Downloading data from the source.   


## **Setup Instructions**

1. **Install Docker and Docker Compose**:
   - Follow the installation instructions for Docker from the [official Docker website](https://docs.docker.com/get-docker/).
   - Install Docker Compose using the instructions [here](https://docs.docker.com/compose/install/).

2. **Clone the Repository**:
   ```sh
   git clone <repository-url>
   cd <repository-directory>
   ```

3. **Create and Activate a Virtual Environment**:

   **For Unix/macOS**:
     ```sh
     python3 -m venv venv
     source venv/bin/activate
     ```
   **For Windows**:
     ```sh
     python -m venv venv
     venv\Scripts\activate
     ```

4. **Install Dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

5. **Build and Run Docker Containers**:
   ```sh
   docker-compose up --build
   ```

6. **Setup Environment Variables**:
   - Ensure the following environment variables are set in your Docker environment or `.env` file:
     - `POSTGRES_USER`
     - `POSTGRES_PASSWORD`
     - `DB_HOST`
     - `POSTGRES_DB`
     - `BATCH_SIZE`
     - `TABLE_NAME`

7. **Access Airflow Web Interface**:
   - Open your web browser and navigate to `http://localhost:8081` to access the Airflow UI.
   - Trigger the `setup_database` DAG manually from the Airflow UI if it does not start automatically.

8. **Verify DAG Execution**:
   - Monitor the execution of the `setup_database` and `load_data` DAGs through the Airflow UI.
   - Check logs for debugging and verification.

## **Uninstall Instructions**

**Stop and Remove Docker Containers and Volumes**:

   ```sh
   docker-compose down --volumes --remove-orphans
   ```

## **Notes**

- Ensure that your PostgreSQL instance is properly configured and accessible from the Docker containers.
- Adjust batch sizes and concurrency settings based on your hardware capabilities and data volume to optimize performance.
