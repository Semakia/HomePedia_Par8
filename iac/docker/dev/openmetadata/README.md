# OpenMetadata (DEV)

Data catalog / metadata store + lineage for HOMEPEDIA.
Official OpenMetadata **1.12.10** compose (Postgres variant), adapted for our stack.

## ⚠️ Resources

OpenMetadata requires **6 GiB RAM + 4 vCPUs allocated to Docker** — on top of the
HOMEPEDIA stack. In Docker Desktop: Settings → Resources → Memory ≥ 8 GiB
recommended (so OM + our Spark/Airflow/Postgres can coexist). The local disk
saturated once already, so keep an eye on space (ES + images ≈ a few GB).

## What it runs

| Service | Purpose | Host port |
|---|---|---|
| `openmetadata-server` | API + Web UI | 8585 / 8586 |
| `elasticsearch` | search index | 9200 / 9300 |
| `postgresql` | OM metadata DB (separate from ours) | **5433** (remapped from 5432) |
| `ingestion` | OM's own Airflow for ingestion workflows | **8081** (remapped from 8080) |
| `execute-migrate-all` | one-shot schema migration | — |

Two host ports were remapped to avoid clashing with HOMEPEDIA
(`postgres` 5432, `airflow` 8080). Everything else is the upstream compose as-is.

## Run

```bash
task openmetadata:up   # or: docker compose -f iac/docker/dev/openmetadata/docker-compose.yml up -d
```

- UI: http://localhost:8585 — login `admin@open-metadata.org` / `admin`
- OM Ingestion (Airflow): http://localhost:8081 — `admin` / `admin`

First start is slow (image pulls + migration + ES index bootstrap). Watch with
`task openmetadata:logs -- openmetadata-server`.

```bash
task openmetadata:down   # stop (keeps volumes under ./docker-volume)
```

## Next: ingestion

### Lesson: don't catalog raw partitioned Parquet

The S3 **Datalake** connector catalogs *each* `part-*.parquet` as its own table
(~1700 tables for 100 departements) and OOM-crashed Elasticsearch. Represent the
Silver dataset as a **single logical table** instead (or catalog Gold Postgres
once it exists). The quality bridge below creates that logical table.

## Data quality bridge (quality → OpenMetadata)

`src/data_governance/metadata/openmetadata_sync.py` (host script) reads the
latest quality report our Spark job wrote to S3 (`_quality/dvf/run=*.json`),
creates/updates the logical table `homepedia.silver.dvf.dvf_silver`, and pushes
one TestCase + result per rule into OM's Data Quality tab. It authenticates with
the OM **admin login token** (avoids the ingestion-bot token pitfalls).

```bash
python -m src.data_governance.metadata.openmetadata_sync --dataset dvf
```

Result: 7 test cases (not_empty, prix_m2_in_range, …) visible on the table in OM,
fed by our single source of truth (config/data_quality/rules.yaml).

## TODO (later)

Catalog **Gold Postgres** (clean tables) via OM's Postgres connector and wire
**Airflow** lineage; OM's ingestion container must join `homepedia-net` for those.
