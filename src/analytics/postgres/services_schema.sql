-- =============================================================================
-- HOMEPEDIA - Gold serving schema (PostgreSQL) — SERVICES domain
-- -----------------------------------------------------------------------------
-- Local amenities from INSEE BPE (Base Permanente des Équipements, DS_BPE).
-- Populated by the services_gold ETL via Spark JDBC.
--
-- Counts per commune by BPE domain (A..G) + presence/count of key amenities
-- (médecin, pharmacie, école, supermarché, boulangerie) + an equipment level.
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS services;

CREATE TABLE IF NOT EXISTS services.commune_equipements (
    code_commune       varchar(5)  PRIMARY KEY,
    year               smallint,                          -- BPE vintage (e.g. 2024)
    -- counts by BPE domain
    nb_services        integer     NOT NULL DEFAULT 0,    -- A: services aux particuliers
    nb_commerces       integer     NOT NULL DEFAULT 0,    -- B
    nb_enseignement    integer     NOT NULL DEFAULT 0,    -- C
    nb_sante           integer     NOT NULL DEFAULT 0,    -- D: santé / action sociale
    nb_transport       integer     NOT NULL DEFAULT 0,    -- E
    nb_sport_culture   integer     NOT NULL DEFAULT 0,    -- F: sport / loisir / culture
    nb_tourisme        integer     NOT NULL DEFAULT 0,    -- G
    nb_total           integer     NOT NULL DEFAULT 0,
    -- key amenities (counts; presence = count > 0)
    nb_medecin         integer     NOT NULL DEFAULT 0,    -- D265
    nb_pharmacie       integer     NOT NULL DEFAULT 0,    -- D307
    nb_ecole           integer     NOT NULL DEFAULT 0,    -- C107/C108/C109
    nb_supermarche     integer     NOT NULL DEFAULT 0,    -- B104/B105
    nb_boulangerie     integer     NOT NULL DEFAULT 0,    -- B207
    -- derived equipment level (count of key amenities present)
    niveau_equipement  text,                              -- Sous-équipée..Très équipée
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_services_niveau
    ON services.commune_equipements (niveau_equipement);
