# HOMEPEDIA — Spark image (PROD). Runs the Silver + Gold ETL in local[*] mode
# inside one container on the VPS. Same recipe as the dev image but the project
# code, config and rules are BAKED IN (no bind mounts) so the image is a
# self-contained deployable artifact.
#
#   docker build -f iac/docker/prod/spark/Dockerfile -t homepedia/spark:<tag> .
FROM bitnamilegacy/spark:3.5

USER root

# --- Python deps for our ETL jobs ---
COPY requirements/spark.txt /tmp/spark.txt
RUN pip install --no-cache-dir -r /tmp/spark.txt

# --- S3A connector (versions MUST match the bundled Hadoop 3.3.4) -----------
ENV SPARK_JARS_DIR=/opt/bitnami/spark/jars
RUN curl -fsSL -o $SPARK_JARS_DIR/hadoop-aws-3.3.4.jar \
      https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -fsSL -o $SPARK_JARS_DIR/aws-java-sdk-bundle-1.12.262.jar \
      https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar && \
    curl -fsSL -o $SPARK_JARS_DIR/postgresql-42.7.4.jar \
      https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar

# --- Real passwd entry for UID 1001 (Hadoop UGI + absolute HOME/Ivy) --------
RUN echo "spark:x:1001:0:spark user:/opt/homepedia:/bin/bash" >> /etc/passwd && \
    mkdir -p /opt/homepedia && chown 1001:0 /opt/homepedia && \
    printf 'spark.jars.ivy /opt/homepedia/.ivy2\n' \
      >> /opt/bitnami/spark/conf/spark-defaults.conf

# --- Project code + config (baked, not mounted) -----------------------------
COPY src /opt/homepedia/src
COPY config /opt/homepedia/config
ENV HOME=/opt/homepedia \
    PYTHONPATH=/opt/homepedia:${PYTHONPATH}

USER 1001
