# HOMEPEDIA — Airflow (PROD) image (runs on the VPS alongside the rest).
# Stock Airflow + the Docker CLI (DAG tasks `docker exec` spark-submit into the
# spark container) + providers/ingestion deps + the DAGs, project code and
# config BAKED IN (the dev image bind-mounts them).
#
#   docker build -f iac/docker/prod/airflow/Dockerfile -t homepedia/airflow:<tag> .
FROM apache/airflow:2.10.3-python3.12

USER root

# Static Docker client (no daemon) so tasks can exec into the spark container.
ADD https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz /tmp/docker.tgz
RUN tar -xzf /tmp/docker.tgz --strip-components=1 -C /usr/local/bin docker/docker \
    && rm /tmp/docker.tgz && docker --version

USER airflow

# Providers + ingestion runtime deps (imported at DAG parse time).
#   google -> ComputeEngineStart/StopInstanceOperator (wake/sleep the Spark VM)
#   ssh    -> SSHOperator (run spark-submit on the VM over SSH)
RUN pip install --no-cache-dir \
    "apache-airflow-providers-amazon==9.0.*" \
    "apache-airflow-providers-postgres==5.13.*" \
    "apache-airflow-providers-apache-spark==4.11.*" \
    "apache-airflow-providers-google==10.24.*" \
    "apache-airflow-providers-ssh==3.14.*" \
    "structlog==24.4.*" \
    "python-dotenv==1.0.*"

# Bake the DAGs + the code/config they import. AIRFLOW_HOME=/opt/airflow.
COPY --chown=airflow:root airflow/dags /opt/airflow/dags
COPY --chown=airflow:root src /opt/airflow/src
COPY --chown=airflow:root config /opt/airflow/config

# DAGs do `from utils.tasks_utils import ...` and `import src.*`; expose both.
ENV PYTHONPATH=/opt/airflow/dags:/opt/airflow
