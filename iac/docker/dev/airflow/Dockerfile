# HOMEPEDIA - Airflow (DEV) image.
# Stock Airflow + the Docker CLI (so DAG tasks can `docker exec` spark-submit
# into the spark-master container, where the Spark runtime/jars live) + our
# providers and ingestion deps baked in (no slow/racy startup pip install).
FROM apache/airflow:2.10.3-python3.12

USER root

# Static Docker client binary (no daemon). ADD fetches without needing curl.
ADD https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz /tmp/docker.tgz
RUN tar -xzf /tmp/docker.tgz --strip-components=1 -C /usr/local/bin docker/docker \
    && rm /tmp/docker.tgz \
    && docker --version

USER airflow

# Providers + ingestion runtime deps (structlog is imported at DAG parse via our
# connectors). Baked here instead of _PIP_ADDITIONAL_REQUIREMENTS.
RUN pip install --no-cache-dir \
    "apache-airflow-providers-amazon==9.0.*" \
    "apache-airflow-providers-postgres==5.13.*" \
    "apache-airflow-providers-apache-spark==4.11.*" \
    "structlog==24.4.*" \
    "python-dotenv==1.0.*"
