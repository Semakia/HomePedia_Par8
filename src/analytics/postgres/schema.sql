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
    -- Affordability (precomputed: prix vs revenu_median). Nullable.
    type_commune       text,                              -- e.g. Métropole / Ville moyenne
    affordability_years numeric(6, 1),                    -- years of median income for a typical home
    m2_par_an          numeric(6, 1),                     -- m² buyable per year of median income
    affordability_class text,                             -- Très abordable | Abordable | Tendu | Très tendu
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

-- Intra-city granularity: arrondissements of Paris (75), Lyon (69), Marseille
-- (13). Same housing/affordability shape as a commune, plus parent identity so
-- the API can serve a drill-down from a clicked city.
CREATE TABLE IF NOT EXISTS gold.arrondissement_metrics (
    code_arrondissement varchar(5) NOT NULL,
    year                smallint   NOT NULL,
    nom_arrondissement  text       NOT NULL,
    code_commune_parent varchar(5) NOT NULL,
    nom_commune_parent  text,
    code_departement    varchar(3) NOT NULL,
    region              text,
    population          integer,
    insee_ref_year      smallint,
    revenu_median       numeric(12, 2),
    revenu_ref_year     smallint,
    prix_m2_median      numeric(10, 2),
    prix_m2_mean        numeric(10, 2),
    surface_median      numeric(8, 2),
    nb_transactions     integer    NOT NULL DEFAULT 0,
    longitude           double precision,
    latitude            double precision,
    period_start        date,
    period_end          date,
    updated_at          timestamptz NOT NULL DEFAULT now(),
    type_commune        text,
    affordability_years numeric(6, 1),
    m2_par_an           numeric(6, 1),
    affordability_class text,
    PRIMARY KEY (code_arrondissement, year)
);
CREATE INDEX IF NOT EXISTS ix_arr_metrics_parent
    ON gold.arrondissement_metrics (code_commune_parent);

-- =============================================================================
-- Sibling Gold pipelines, namespaced in their own fixed schemas (NOT under the
-- configurable gold_schema). The API LEFT-joins these onto city_metrics, so a
-- local Gold layer needs them to exist (even empty) for the join to resolve.
-- On the remote dev DB they are populated by the demographics / mobility /
-- services pipelines.
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS demographics;
CREATE SCHEMA IF NOT EXISTS mobility;
CREATE SCHEMA IF NOT EXISTS services;

-- Age structure per commune (INSEE) — drives the "young area" criterion.
CREATE TABLE IF NOT EXISTS demographics.commune_profile (
    code_commune     varchar(5) NOT NULL,
    year             smallint   NOT NULL,
    population_total  integer,
    pct_moins25       numeric(5, 2),
    pct_25_64         numeric(5, 2),
    pct_65plus        numeric(5, 2),
    part_femmes       numeric(5, 2),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (code_commune, year)
);

-- Geolocated train stations (SNCF) — served as a map point layer.
CREATE TABLE IF NOT EXISTS mobility.gares (
    code_uic          varchar(16) NOT NULL,
    nom_gare          text        NOT NULL,
    code_commune      varchar(5),
    segment_drg       varchar(2),                       -- A | B | C
    frequentation     integer,
    frequentation_year smallint,
    longitude         double precision,
    latitude          double precision,
    updated_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (code_uic)
);

-- Rail access summarized per commune (nearest station, service level).
CREATE TABLE IF NOT EXISTS mobility.commune_transport (
    code_commune        varchar(5) NOT NULL,
    nb_gares            integer,
    frequentation_totale bigint,
    frequentation_year   smallint,
    best_segment_drg     varchar(2),
    desserte_class       text,                          -- Hub majeur | Bien desservie | Desservie | Non desservie
    distance_gare_km     numeric(6, 2),
    gare_proche_uic      varchar(16),
    gare_proche_nom      text,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (code_commune)
);

-- Amenities / facility counts per commune (INSEE BPE) — quality of life.
CREATE TABLE IF NOT EXISTS services.commune_equipements (
    code_commune     varchar(5) NOT NULL,
    year             smallint   NOT NULL,
    nb_services       integer,
    nb_commerces      integer,
    nb_enseignement   integer,
    nb_sante          integer,
    nb_transport      integer,
    nb_sport_culture  integer,
    nb_tourisme       integer,
    nb_total          integer,
    nb_medecin        integer,
    nb_pharmacie      integer,
    nb_ecole          integer,
    nb_supermarche    integer,
    nb_boulangerie    integer,
    niveau_equipement text,                             -- Très équipée | Bien équipée | Équipée | Sous-équipée
    updated_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (code_commune, year)
);
