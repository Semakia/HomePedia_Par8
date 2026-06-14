-- =============================================================================
-- HOMEPEDIA - Gold layer schema (PostgreSQL)
-- -----------------------------------------------------------------------------
-- Query-optimized, PRE-AGGREGATED tables served by the FastAPI backend.
-- Populated by the silver_to_gold ETL (DVF + INSEE). INSEE-derived columns are
-- nullable so the API contract is stable before INSEE lands.
--
-- No foreign keys between the tables: the ETL rebuilds Gold wholesale
-- (truncate + load via Spark JDBC), so consistency is ETL-guaranteed and FKs
-- would only block the reload order. Idempotent: safe to re-run.
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS gold;

-- One row per commune AND per DVF year: yearly housing metrics + reference dims.
-- The API surfaces the most recent year as the headline (DISTINCT ON), and can
-- expose the full per-year history. Aggregating per year avoids mixing prices
-- across vintages (real-estate inflation bias).
CREATE TABLE IF NOT EXISTS gold.city_metrics (
    code_commune       varchar(5)  NOT NULL,             -- INSEE code (join key)
    year               smallint    NOT NULL,             -- DVF transaction year
    nom_commune        text        NOT NULL,
    code_departement   varchar(3)  NOT NULL,
    -- INSEE enrichment (nullable until the INSEE pipeline lands)
    region             text,
    population         integer,
    insee_ref_year     smallint,                          -- INSEE population vintage (e.g. 2022), for millésime transparency
    revenu_median      numeric(12, 2),                    -- FiLoSoFi median standard of living (€/yr)
    revenu_ref_year    smallint,                          -- FiLoSoFi income vintage (e.g. 2023), distinct from population
    -- DVF-derived housing metrics (for this year)
    prix_m2_median     numeric(10, 2),
    prix_m2_mean       numeric(10, 2),
    surface_median     numeric(8, 2),
    nb_transactions    integer     NOT NULL DEFAULT 0,
    -- geo + provenance
    longitude          double precision,
    latitude           double precision,
    period_start       date,
    period_end         date,
    updated_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (code_commune, year)
);

CREATE INDEX IF NOT EXISTS ix_city_metrics_departement
    ON gold.city_metrics (code_departement);
CREATE INDEX IF NOT EXISTS ix_city_metrics_prix_m2
    ON gold.city_metrics (prix_m2_median);
CREATE INDEX IF NOT EXISTS ix_city_metrics_nom
    ON gold.city_metrics (lower(nom_commune));
-- Headline lookup = latest year per commune.
CREATE INDEX IF NOT EXISTS ix_city_metrics_code_year
    ON gold.city_metrics (code_commune, year DESC);

-- Monthly price trend per commune (for the city-detail view / charts).
CREATE TABLE IF NOT EXISTS gold.city_price_trend (
    code_commune       varchar(5)  NOT NULL,
    year               smallint    NOT NULL,
    month              smallint    NOT NULL CHECK (month BETWEEN 1 AND 12),
    prix_m2_median     numeric(10, 2),
    nb_transactions    integer     NOT NULL DEFAULT 0,
    PRIMARY KEY (code_commune, year, month)
);

-- Housing metrics broken down by dwelling type (Maison / Appartement).
CREATE TABLE IF NOT EXISTS gold.housing_price_by_type (
    code_commune       varchar(5)  NOT NULL,
    type_local         varchar(20) NOT NULL,           -- Maison | Appartement
    prix_m2_median     numeric(10, 2),
    surface_median     numeric(8, 2),
    nb_transactions    integer     NOT NULL DEFAULT 0,
    PRIMARY KEY (code_commune, type_local)
);
