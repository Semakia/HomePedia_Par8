# HOMEPEDIA - Spark image (Silver ETL), master & worker share this image.
# Bitnami Spark 3.5 (Hadoop 3.3.4, Java 17) + S3A connector + project code,
# runnable as the default non-root user (UID 1001) against AWS S3 or MinIO,
# with NO submit-time hacks (jars, UGI login, Ivy home all handled here).
FROM bitnamilegacy/spark:3.5

USER root

# --- Python deps for our ETL jobs ---
COPY requirements/spark.txt /tmp/spark.txt
RUN pip install --no-cache-dir -r /tmp/spark.txt

# --- S3A connector ---
# hadoop-aws MUST match the bundled Hadoop (3.3.4); aws-java-sdk-bundle MUST be
# the exact version hadoop-aws:3.3.4 depends on (1.12.262). Mismatch => runtime
# NoSuchMethod / ClassNotFound. Baking them avoids --packages at submit time.
ENV SPARK_JARS_DIR=/opt/bitnami/spark/jars
RUN curl -fsSL -o $SPARK_JARS_DIR/hadoop-aws-3.3.4.jar \
      https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -fsSL -o $SPARK_JARS_DIR/aws-java-sdk-bundle-1.12.262.jar \
      https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

# PostgreSQL JDBC driver so Spark can write the Gold layer.
RUN curl -fsSL -o $SPARK_JARS_DIR/postgresql-42.7.4.jar \
      https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar

# --- Make UID 1001 a real user ---
# Without a passwd entry, getpwuid(1001) returns null -> Hadoop UGI login fails
# ("invalid null input: name") and Ivy/Spark have no absolute HOME.
RUN echo "spark:x:1001:0:spark user:/opt/homepedia:/bin/bash" >> /etc/passwd && \
    mkdir -p /opt/homepedia && chown 1001:0 /opt/homepedia

# --- Spark defaults: Ivy cache in a writable absolute dir ---
RUN printf 'spark.jars.ivy /opt/homepedia/.ivy2\n' \
    >> /opt/bitnami/spark/conf/spark-defaults.conf

# --- Project code ---
# COPY for a standalone image; the dev compose bind-mounts repo src over
# /opt/homepedia/src for hot reload. PYTHONPATH makes `import src.*` resolve.
COPY src /opt/homepedia/src
ENV HOME=/opt/homepedia
ENV PYTHONPATH=/opt/homepedia:${PYTHONPATH}

USER 1001
