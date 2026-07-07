"""Spark-execution operator factories for the ETL DAGs.

The same DAGs run in two modes, switched by env so dev and prod share one code
path:

* **local** (dev): Spark runs in a local container; tasks ``docker exec`` into
  it. This is the default, used whenever ``SPARK_SSH_CONN_ID`` is unset.
* **remote** (prod): Spark runs on an on-demand GCP VM. Airflow starts the VM,
  waits for the container to be reachable, SSHes in to run ``spark-submit``,
  then stops the VM again (even on failure, to save cost). Selected as soon as
  ``SPARK_SSH_CONN_ID`` is set.

Keeping these factories here (not inline in the DAG files) honours the project
rule "no functions in the DAG files": the DAGs just call these builders and wire
the returned operators.
"""

from __future__ import annotations

import os
from datetime import timedelta

from airflow.models.baseoperator import BaseOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

SPARK_CONTAINER = os.getenv("SPARK_CONTAINER", "homepedia-dev-spark-master")
SPARK_SSH_CONN_ID = os.getenv("SPARK_SSH_CONN_ID")  # set -> remote (prod)
GCP_PROJECT = os.getenv("GCP_PROJECT", "")
GCP_ZONE = os.getenv("GCP_ZONE", "")
GCP_INSTANCE = os.getenv("GCP_INSTANCE", "")

# An SSH connection to the Spark VM being configured is what flips us to remote.
REMOTE = bool(SPARK_SSH_CONN_ID)


def spark_submit(task_id: str, submit_args: str) -> BaseOperator:
    """Build one spark-submit task (local ``docker exec``, or remote over SSH).

    ``submit_args`` is everything after ``--master 'local[*]'`` (the app path and
    its flags). If it contains Jinja such as ``{{ params.year }}``, pass it as a
    plain concatenated string (never inside an f-string) so the braces survive.
    """
    submit = f"spark-submit --master 'local[*]' {submit_args}"
    command = f'docker exec {SPARK_CONTAINER} bash -c "{submit}"'
    if REMOTE:
        from airflow.providers.ssh.operators.ssh import SSHOperator

        return SSHOperator(
            task_id=task_id,
            ssh_conn_id=SPARK_SSH_CONN_ID,
            command=command,
            conn_timeout=60,
            cmd_timeout=7200,
        )
    return BashOperator(task_id=task_id, bash_command=command)


def start_spark_cluster(task_id: str = "start_spark_vm") -> BaseOperator:
    """Start the on-demand Spark VM (no-op in local/dev mode)."""
    if not REMOTE:
        return EmptyOperator(task_id=task_id)
    from airflow.providers.google.cloud.operators.compute import (
        ComputeEngineStartInstanceOperator,
    )

    return ComputeEngineStartInstanceOperator(
        task_id=task_id,
        project_id=GCP_PROJECT,
        zone=GCP_ZONE,
        resource_id=GCP_INSTANCE,
    )


def wait_spark_ready(task_id: str = "wait_spark_ready") -> BaseOperator:
    """Block until the Spark container answers on the VM (no-op in dev mode).

    Retries absorb the SSH-not-up-yet window right after the VM boots; the inner
    loop then waits for the ``homepedia-spark-master`` container to be exec-able.
    """
    if not REMOTE:
        return EmptyOperator(task_id=task_id)
    from airflow.providers.ssh.operators.ssh import SSHOperator

    probe = (
        f"timeout 300 sh -c 'until docker exec {SPARK_CONTAINER} true 2>/dev/null; "
        f"do sleep 5; done'"
    )
    return SSHOperator(
        task_id=task_id,
        ssh_conn_id=SPARK_SSH_CONN_ID,
        command=probe,
        conn_timeout=60,
        cmd_timeout=360,
        retries=10,
        retry_delay=timedelta(seconds=20),
    )


def stop_spark_cluster(task_id: str = "stop_spark_vm") -> BaseOperator:
    """Stop the Spark VM. Runs even if an upstream task failed (cost control)."""
    if not REMOTE:
        return EmptyOperator(task_id=task_id)
    from airflow.providers.google.cloud.operators.compute import (
        ComputeEngineStopInstanceOperator,
    )

    return ComputeEngineStopInstanceOperator(
        task_id=task_id,
        project_id=GCP_PROJECT,
        zone=GCP_ZONE,
        resource_id=GCP_INSTANCE,
        trigger_rule="all_done",
    )
