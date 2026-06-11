-- =============================================================================
-- HOMEPEDIA - Gold layer schema (PostgreSQL)
-- -----------------------------------------------------------------------------
-- Query-optimized, PRE-AGGREGATED tables served by the FastAPI backend.
-- Populated by the silver_to_gold ETL (DVF + INSEE). INSEE-derived columns are
-- nullable so the API contract is stable before INSEE lands.
-- Idempotent: safe to re-run.
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS gold;

-- One row per commune: headline metrics + reference dims (INSEE nullable).
CREATE TABLE IF NOT EXISTS gold.city_metrics (
    code_commune       varchar(5)  PRIMARY KEY,         -- INSEE code (join key)
    nom_commune        text        NOT NULL,
    code_departement   varchar(3)  NOT NULL,
    -- INSEE enrichment (nullable until the INSEE pipeline lands)
    region             text,
    population         integer,
    revenu_median      numeric(12, 2),
    -- DVF-derived housing metrics
    prix_m2_median     numeric(10, 2),
    prix_m2_mean       numeric(10, 2),
    surface_median     numeric(8, 2),
    nb_transactions    integer     NOT NULL DEFAULT 0,
    -- geo + provenance
    longitude          double precision,
    latitude           double precision,
    period_start       date,
    period_end         date,
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_city_metrics_departement
    ON gold.city_metrics (code_departement);
CREATE INDEX IF NOT EXISTS ix_city_metrics_prix_m2
    ON gold.city_metrics (prix_m2_median);
CREATE INDEX IF NOT EXISTS ix_city_metrics_nom
    ON gold.city_metrics (lower(nom_commune));

-- Monthly price trend per commune (for the city-detail view / charts).
CREATE TABLE IF NOT EXISTS gold.city_price_trend (
    code_commune       varchar(5)  NOT NULL
        REFERENCES gold.city_metrics (code_commune) ON DELETE CASCADE,
    year               smallint    NOT NULL,
    month              smallint    NOT NULL CHECK (month BETWEEN 1 AND 12),
    prix_m2_median     numeric(10, 2),
    nb_transactions    integer     NOT NULL DEFAULT 0,
    PRIMARY KEY (code_commune, year, month)
);

-- Housing metrics broken down by dwelling type (Maison / Appartement).
CREATE TABLE IF NOT EXISTS gold.housing_price_by_type (
    code_commune       varchar(5)  NOT NULL
        REFERENCES gold.city_metrics (code_commune) ON DELETE CASCADE,
    type_local         varchar(20) NOT NULL,           -- Maison | Appartement
    prix_m2_median     numeric(10, 2),
    surface_median     numeric(8, 2),
    nb_transactions    integer     NOT NULL DEFAULT 0,
    PRIMARY KEY (code_commune, type_local)
);
