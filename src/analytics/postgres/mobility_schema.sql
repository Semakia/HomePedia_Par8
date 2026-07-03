-- =============================================================================
-- HOMEPEDIA - Gold serving schema (PostgreSQL) — MOBILITY domain
-- -----------------------------------------------------------------------------
-- Train-station accessibility from SNCF open data (gares-de-voyageurs +
-- frequentation-gares). Populated by the mobility_gold ETL via Spark JDBC.
--
-- Only communes WITH at least one station appear in commune_transport; the
-- absence of a row means "not served" (the API treats it as such).
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS mobility;

-- One row per passenger station (for maps / detail).
CREATE TABLE IF NOT EXISTS mobility.gares (
    code_uic           varchar(10) PRIMARY KEY,           -- SNCF UIC code
    nom_gare           text        NOT NULL,
    code_commune       varchar(5),                        -- INSEE code (join key)
    segment_drg        varchar(2),                        -- A (hub) / B / C
    frequentation      integer,                           -- annual passengers
    frequentation_year smallint,
    longitude          double precision,
    latitude           double precision,
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_gares_commune
    ON mobility.gares (code_commune);

-- One row per commune (with coordinates): station count + traffic + desserte
-- class + distance to the nearest station. Unserved communes have nb_gares=0,
-- desserte_class='Non desservie' and a non-null distance to the closest gare
-- (haversine, no external geocoding service).
CREATE TABLE IF NOT EXISTS mobility.commune_transport (
    code_commune         varchar(5)  PRIMARY KEY,
    nb_gares             integer     NOT NULL DEFAULT 0,
    frequentation_totale bigint,                          -- summed over the stations
    frequentation_year   smallint,
    best_segment_drg     varchar(2),                      -- best (A < B < C)
    desserte_class       text,                            -- Hub majeur / Bien desservie / Desservie / Non desservie
    distance_gare_km     numeric(7, 2),                   -- as-the-crow-flies to nearest station (0 if served)
    gare_proche_uic      varchar(10),                     -- nearest station (for unserved communes)
    gare_proche_nom      text,
    updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_commune_transport_class
    ON mobility.commune_transport (desserte_class);
