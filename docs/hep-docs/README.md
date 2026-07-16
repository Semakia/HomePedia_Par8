# HOMEPEDIA - Repository Structure

```
homepedia/
│
├── .github/
│   ├── workflows/
│   │   ├── ci-tests.yml           # Run tests on push
│   │   ├── deploy-dev.yml         # Deploy to dev environment
│   │   ├── deploy-prod.yml        # Deploy to production
│   │   └── data-quality-checks.yml # Run Great Expectations tests
│   │
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── data_quality_issue.md
│   │
│   └── pull_request_template.md
│
├── docs/
│   ├── README.md                  # Main documentation
│   ├── ARCHITECTURE.md            # System design & data flow
│   ├── DATA_GOVERNANCE.md         # Governance framework
│   ├── API_REFERENCE.md           # FastAPI endpoints
│   ├── SETUP.md                   # Installation & setup
│   ├── CONTRIBUTING.md            # Contribution guidelines
│   ├── DATA_DICTIONARY.md         # Column definitions, owners
│   │
│   ├── diagrams/
│   │   ├── architecture.png
│   │   ├── data_flow.png
│   │   ├── governance_framework.png
│   │   └── medallion_layers.png
│   │
│   └── runbooks/
│       ├── incident_response.md
│       ├── data_refresh_manual.md
│       ├── disaster_recovery.md
│       └── troubleshooting.md
│
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf               # Main infrastructure
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── vpc.tf               # VPC, subnets
│   │   ├── s3.tf                # S3 buckets (Bronze, Silver)
│   │   ├── rds.tf               # PostgreSQL + RDS
│   │   ├── ec2.tf               # VPS instances (Spark, ClickHouse)
│   │   ├── iam.tf               # IAM roles & policies
│   │   └── monitoring.tf        # CloudWatch alarms
│   │
│   ├── docker/
│   │   ├── Dockerfile.spark     # Spark cluster image
│   │   ├── Dockerfile.airflow   # Airflow image
│   │   ├── Dockerfile.api       # FastAPI image
│   │   ├── Dockerfile.frontend  # Streamlit image
│   │   └── docker-compose.yml   # Local dev environment
│   │
│   ├── k8s/
│   │   ├── namespace.yaml
│   │   ├── deployments/
│   │   │   ├── airflow.yaml
│   │   │   ├── api.yaml
│   │   │   ├── frontend.yaml
│   │   │   └── spark-operator.yaml
│   │   ├── services/
│   │   ├── configmaps/
│   │   └── secrets/
│   │
│   └── scripts/
│       ├── init_databases.sh    # Setup PostgreSQL, ClickHouse, etc
│       ├── create_s3_buckets.sh
│       ├── setup_iam_roles.sh
│       └── deploy.sh            # Deployment automation
│
├── src/
│   │
│   ├── data_ingestion/          # LAYER 1: Ingest raw data
│   │   ├── __init__.py
│   │   ├── sources/
│   │   │   ├── mapbox_connector.py
│   │   │   ├── sncf_connector.py
│   │   │   ├── insee_connector.py
│   │   │   ├── seloger_scraper.py
│   │   │   ├── pap_scraper.py
│   │   │   └── web_scraper.py
│   │   ├── loaders/
│   │   │   ├── s3_loader.py     # Load to Bronze S3
│   │   │   ├── schema_validator.py
│   │   │   └── metadata_registrar.py
│   │   └── utils/
│   │       ├── http_client.py
│   │       ├── retry_logic.py
│   │       └── logging_utils.py
│   │
│   ├── data_processing/         # LAYER 2-3: Bronze → Silver ETL
│   │   ├── __init__.py
│   │   ├── transformations/
│   │   │   ├── housing_etl.py
│   │   │   ├── employment_etl.py
│   │   │   ├── transport_etl.py
│   │   │   ├── amenities_etl.py
│   │   │   ├── crime_etl.py
│   │   │   └── reviews_etl.py
│   │   ├── quality/
│   │   │   ├── validators.py    # Great Expectations
│   │   │   ├── schema_checks.py
│   │   │   ├── completeness_checks.py
│   │   │   ├── freshness_checks.py
│   │   │   └── anomaly_detection.py
│   │   ├── aggregations/
│   │   │   ├── city_metrics.py
│   │   │   ├── affordability_index.py
│   │   │   └── pre_computed_views.py
│   │   └── utils/
│   │       ├── spark_utils.py
│   │       ├── data_cleaner.py
│   │       └── geo_utils.py
│   │
│   ├── data_governance/         # Governance layer
│   │   ├── __init__.py
│   │   ├── metadata/
│   │   │   ├── metadata_store.py  # Lineage tracking
│   │   │   ├── data_catalog.py    # Dataset registry
│   │   │   └── column_profiler.py
│   │   ├── quality/
│   │   │   ├── quality_monitor.py
│   │   │   ├── data_quality_reporter.py
│   │   │   └── sla_checker.py
│   │   ├── security/
│   │   │   ├── rbac.py            # Role-based access control
│   │   │   ├── data_masking.py
│   │   │   └── audit_logger.py
│   │   ├── compliance/
│   │   │   ├── gdpr_handler.py
│   │   │   ├── retention_manager.py
│   │   │   └── change_tracker.py
│   │   └── policies/
│   │       ├── access_policies.yaml
│   │       ├── retention_policies.yaml
│   │       └── sensitivity_levels.yaml
│   │
│   ├── analytics/               # LAYER 4: Gold - Analytics
│   │   ├── __init__.py
│   │   ├── duckdb/
│   │   │   ├── queries.py
│   │   │   ├── view_definitions.sql
│   │   │   └── index_strategy.sql
│   │   ├── postgresql/
│   │   │   ├── schema.sql
│   │   │   ├── procedures.sql
│   │   │   └── migrations/
│   │   ├── clickhouse/
│   │   │   ├── tables.sql
│   │   │   ├── aggregations.sql
│   │   │   └── compression_policies.sql
│   │   ├── elasticsearch/
│   │   │   ├── index_mappings.json
│   │   │   ├── analyzers.json
│   │   │   └── bulk_indexing.py
│   │   └── mongodb/
│   │       ├── schemas.json
│   │       └── aggregation_pipelines.py
│   │
│   ├── api/                     # FastAPI Backend
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings & env vars
│   │   ├── dependencies.py      # Database connections
│   │   ├── auth/
│   │   │   ├── jwt_handler.py
│   │   │   ├── oauth_provider.py
│   │   │   └── permissions.py
│   │   ├── routers/
│   │   │   ├── housing.py       # /api/housing/*
│   │   │   ├── cities.py        # /api/cities/*
│   │   │   ├── employment.py
│   │   │   ├── transport.py
│   │   │   ├── amenities.py
│   │   │   ├── crime.py
│   │   │   ├── search.py        # Full-text search
│   │   │   └── admin.py         # Admin endpoints
│   │   ├── schemas/
│   │   │   ├── housing.py       # Pydantic models
│   │   │   ├── city.py
│   │   │   └── responses.py
│   │   ├── models/
│   │   │   └── database.py      # SQLAlchemy ORM
│   │   ├── services/
│   │   │   ├── housing_service.py
│   │   │   ├── search_service.py
│   │   │   └── analytics_service.py
│   │   ├── middleware/
│   │   │   ├── cors.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── request_logger.py
│   │   │   └── error_handler.py
│   │   └── tests/
│   │       ├── test_housing.py
│   │       ├── test_cities.py
│   │       ├── conftest.py      # Pytest fixtures
│   │       └── factories.py     # Test data factories
│   │
│   ├── frontend/               # Streamlit Dashboard
│   │   ├── __init__.py
│   │   ├── app.py              # Main Streamlit app
│   │   ├── config.py
│   │   ├── pages/
│   │   │   ├── 1_overview.py
│   │   │   ├── 2_city_explorer.py
│   │   │   ├── 3_affordability.py
│   │   │   ├── 4_market_analysis.py
│   │   │   ├── 5_sentiment.py
│   │   │   └── 6_admin.py
│   │   ├── components/
│   │   │   ├── map_widget.py
│   │   │   ├── metrics_cards.py
│   │   │   ├── charts.py
│   │   │   └── filters.py
│   │   ├── services/
│   │   │   ├── api_client.py
│   │   │   ├── cache_manager.py
│   │   │   └── data_loader.py
│   │   └── tests/
│   │       └── test_pages.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py             # Configuration management
│       ├── logging.py            # Structured logging
│       ├── database.py           # DB connection pooling
│       ├── s3_utils.py
│       ├── monitoring.py         # Metrics & alerts
│       └── constants.py
│
├── airflow/                      # Orchestration Layer
│   ├── dags/
│   │   ├── homepedia_etl.py     # Main ETL DAG
│   │   ├── data_quality_dag.py  # Quality checks
│   │   ├── governance_dag.py    # Governance tasks
│   │   └── utils.py             # Shared utilities
│   ├── plugins/
│   │   ├── operators/
│   │   │   ├── s3_to_spark_operator.py
│   │   │   ├── quality_check_operator.py
│   │   │   └── metadata_logger_operator.py
│   │   └── sensors/
│   │       ├── s3_file_sensor.py
│   │       └── data_freshness_sensor.py
│   ├── config/
│   │   └── airflow.cfg
│   └── scripts/
│       ├── init_airflow.sh
│       └── create_connections.py
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_transformations.py
│   │   ├── test_validators.py
│   │   ├── test_api_endpoints.py
│   │   └── test_governance.py
│   ├── integration/
│   │   ├── test_bronze_to_silver.py
│   │   ├── test_silver_to_gold.py
│   │   ├── test_end_to_end.py
│   │   └── test_api_database.py
│   ├── performance/
│   │   ├── test_query_latency.py
│   │   ├── test_ingestion_throughput.py
│   │   └── test_api_load.py
│   ├── fixtures/
│   │   ├── sample_data.py
│   │   ├── mock_apis.py
│   │   └── test_databases.py
│   └── conftest.py              # Pytest configuration
│
├── config/
│   ├── development.yaml          # Dev environment config
│   ├── staging.yaml
│   ├── production.yaml
│   ├── data_quality_rules.yaml
│   ├── access_policies.yaml
│   ├── retention_policies.yaml
│   └── monitoring_alerts.yaml
│
├── notebooks/                    # Jupyter Notebooks
│   ├── exploratory/
│   │   ├── eda_housing_data.ipynb
│   │   ├── price_trends.ipynb
│   │   └── sentiment_analysis.ipynb
│   ├── analysis/
│   │   ├── affordability_analysis.ipynb
│   │   └── market_segmentation.ipynb
│   └── documentation/
│       └── data_walkthrough.ipynb
│
├── scripts/
│   ├── setup/
│   │   ├── init_databases.py    # Initialize all DBs
│   │   ├── create_s3_structure.py
│   │   ├── seed_data.py         # Load initial data
│   │   └── setup_monitoring.py
│   ├── data_ops/
│   │   ├── manual_refresh.py    # Manual data refresh
│   │   ├── backfill_data.py
│   │   └── validate_all_data.py
│   ├── governance/
│   │   ├── audit_data_access.py
│   │   ├── purge_old_data.py
│   │   └── generate_lineage_report.py
│   └── maintenance/
│       ├── optimize_indexes.py
│       ├── update_statistics.py
│       └── backup_metadata.py
│
├── sql/                          # SQL scripts
│   ├── migrations/
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_add_timeseries.sql
│   │   └── 003_add_governance_tables.sql
│   ├── queries/
│   │   ├── analytics/
│   │   │   ├── city_affordability.sql
│   │   │   ├── price_trends.sql
│   │   │   └── market_analysis.sql
│   │   └── governance/
│   │       ├── data_lineage.sql
│   │       ├── quality_metrics.sql
│   │       └── access_audit.sql
│   └── views/
│       ├── materialized_views.sql
│       └── duckdb_views.sql
│
├── requirements/
│   ├── base.txt                 # Core dependencies
│   ├── dev.txt                  # Dev dependencies
│   ├── test.txt                 # Test dependencies
│   ├── ml.txt                   # ML libraries
│   └── airflow.txt              # Airflow + plugins
│
├── Dockerfile                    # Production image
├── docker-compose.yml            # Local development
├── .dockerignore
│
├── .env.example                  # Environment variables template
├── .gitignore
├── .pre-commit-config.yaml       # Code quality checks
│
├── setup.py                      # Package installation
├── pyproject.toml               # Poetry config (alternative)
├── Makefile                     # Common commands
│
├── LICENSE
├── README.md                     # Main README
└── CHANGELOG.md                  # Version history
```

---

## 📋 File Descriptions by Category

### **1. Data Ingestion Layer** (`src/data_ingestion/`)
```
Purpose: Collect data from multiple sources → Bronze (S3)

Key Files:
- mapbox_connector.py       : Fetch geographic/transport data
- sncf_connector.py         : Train station & routes data
- seloger_scraper.py        : Web scraping Seloger.com
- s3_loader.py              : Write raw data to Bronze S3
- metadata_registrar.py     : Log data arrival in catalog
```

### **2. Data Processing (ETL)** (`src/data_processing/`)
```
Purpose: Bronze → Silver transformations with quality checks

Key Files:
- housing_etl.py            : Clean & normalize housing prices
- quality/validators.py     : Great Expectations tests
- completeness_checks.py    : Check for nulls, missing values
- freshness_checks.py       : Ensure data is current
- aggregations/city_metrics.py : Pre-compute city-level stats
```

### **3. Data Governance** (`src/data_governance/`)
```
Purpose: Enforce policies, track lineage, ensure compliance

Key Files:
- metadata/metadata_store.py : Track source → transformations → outputs
- quality/quality_monitor.py : Monitor data quality metrics
- security/rbac.py          : Role-based access control
- compliance/gdpr_handler.py : Handle deletion requests
- compliance/retention_manager.py : Archive/delete old data
```

### **4. Analytics Layer (Gold)** (`src/analytics/`)
```
Purpose: Query-optimized databases for different use cases

Key Files:
- duckdb/queries.py         : Fast OLAP queries
- postgresql/schema.sql     : Relational tables + time-series
- clickhouse/aggregations.sql : Pre-aggregated metrics
- elasticsearch/            : Full-text search on reviews
- mongodb/                  : Document storage for flexible data
```

### **5. API Backend** (`src/api/`)
```
Purpose: REST API to query Gold layer databases

Key Files:
- routers/housing.py        : GET /api/housing/{city_id}
- routers/search.py         : Full-text search endpoint
- services/housing_service.py : Business logic
- middleware/rbac.py        : Enforce access control
- middleware/audit_logger.py : Log all queries
```

### **6. Frontend** (`src/frontend/`)
```
Purpose: Interactive dashboards for users

Key Files:
- pages/1_overview.py       : Main dashboard
- pages/2_city_explorer.py  : Browse individual cities
- pages/3_affordability.py  : Affordability analysis
- components/map_widget.py  : Interactive maps
- services/api_client.py    : Call FastAPI endpoints
```

### **7. Orchestration** (`airflow/dags/`)
```
Purpose: Schedule & monitor data pipelines

Key Files:
- homepedia_etl.py          : Main ETL workflow
  → Trigger at 2 AM daily
  → Run data ingestion
  → Run Bronze → Silver ETL
  → Run quality checks
  → Load to Gold databases
  → Update cache
- data_quality_dag.py       : Run quality metrics every 6 hours
- governance_dag.py         : Run compliance checks
```

---

## 🚀 Quick Start Setup

### **Initialize Repository**

```bash
# Clone
git clone https://github.com/yourorg/homepedia.git
cd homepedia

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/base.txt
pip install -r requirements/dev.txt

# Setup pre-commit hooks
pre-commit install

# Initialize databases
python scripts/setup/init_databases.py

# Start local environment
docker-compose up -d
```

### **Run Tests**

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=src tests/
```

### **Run Data Pipeline**

```bash
# Local Airflow
airflow standalone

# Or via Docker
docker-compose exec airflow airflow dags trigger homepedia_etl

# Or manually
python -m src.data_processing.transformations.housing_etl
```

---

## 📊 Development Workflow

### **1. Add New Data Source**

```python
# 1. Create connector in src/data_ingestion/sources/
# src/data_ingestion/sources/new_source.py

# 2. Add loader logic
# Modify src/data_ingestion/loaders/s3_loader.py

# 3. Register in metadata catalog
# Update config/data_quality_rules.yaml

# 4. Add ingestion task to Airflow
# airflow/dags/homepedia_etl.py → add_task()

# 5. Test
# pytest tests/unit/test_new_source.py
```

### **2. Add New Analysis (Gold Layer)**

```sql
-- 1. Create view in SQL
-- sql/views/duckdb_views.sql

CREATE VIEW my_analysis AS
SELECT city_id, 
       AVG(price_m2) as avg_price
FROM housing_prices
GROUP BY city_id;

-- 2. Add endpoint in FastAPI
-- src/api/routers/analysis.py

@router.get("/api/analysis/{city_id}")
def get_my_analysis(city_id: int):
    return service.analyze(city_id)

-- 3. Add dashboard page
-- src/frontend/pages/7_my_analysis.py

-- 4. Test
pytest tests/unit/test_api_endpoints.py
```

### **3. Modify Data Quality Rules**

```yaml
# config/data_quality_rules.yaml

housing_prices:
  schema:
    city_id: INTEGER NOT NULL
    price_m2: DECIMAL NOT NULL
  completeness:
    required_cols: [city_id, price_m2]
    max_null_pct: 5
  freshness:
    max_age_hours: 24
  ranges:
    price_m2: [1000, 50000]
```

---

## 🔐 Security & Governance

### **Access Control**

```yaml
# config/access_policies.yaml

roles:
  public_user:
    datasets:
      - affordability_index
      - crime_stats
    operations: [read]
  
  analyst:
    datasets:
      - housing_prices
      - employment_stats
    operations: [read]
  
  admin:
    datasets: ["*"]
    operations: [read, write, delete]
```

### **Data Retention**

```yaml
# config/retention_policies.yaml

housing_prices:
  keep_years: 5
  archive_years: 2
  action: compress_and_move_to_glacier

reviews:
  keep_years: 3
  action: anonymize_then_archive
```

---

## 📈 Monitoring & Alerting

### **Key Metrics to Track**

```yaml
# config/monitoring_alerts.yaml

metrics:
  data_freshness:
    - housing_prices_last_update > 24h → alert
  data_quality:
    - null_rate > 5% → alert
    - duplicate_rate > 2% → alert
  api_performance:
    - p95_latency > 500ms → alert
    - error_rate > 1% → alert
  storage:
    - s3_cost > $1000/month → alert
```

---

## 🎯 Key Principles

1. **Modularity** : Each layer is independent, testable, deployable
2. **Governance** : Lineage, quality, security at every stage
3. **Scalability** : Handle 650+ GB with Spark + distributed DBs
4. **Testability** : Unit + integration + performance tests
5. **Documentation** : Self-documenting code + runbooks
6. **Automation** : CI/CD, data validation, monitoring

---

## 💡 Next Steps

1. **Create the repo** with this structure
2. **Set up CI/CD** with GitHub Actions
3. **Deploy infrastructure** with Terraform
4. **Implement data sources** (connectors)
5. **Build ETL jobs** (Bronze → Silver)
6. **Create analytics queries** (Gold layer)
7. **Build API** (FastAPI endpoints)
8. **Build dashboards** (Streamlit)
9. **Enable governance** (metadata, quality, security)

---

## 📚 References

- Medallion Architecture: https://docs.databricks.com/en/lakehouse/medallion.html
- Great Expectations: https://greatexpectations.io/
- Apache Airflow: https://airflow.apache.org/
- FastAPI: https://fastapi.tiangolo.com/
- Streamlit: https://docs.streamlit.io/