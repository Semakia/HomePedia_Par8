-- HOMEPEDIA — Gold column/table documentation (source of truth for OpenMetadata).
--
-- The served Gold tables are written by Spark JDBC with truncate=true (TRUNCATE +
-- reload, NOT DROP/CREATE), so these COMMENTs survive every ETL run. OpenMetadata's
-- Postgres connector reads them as table/column descriptions on the next ingestion.
--
-- Apply once (and after any schema change):
--   psql "$DATABASE_URL" -f src/data_governance/metadata/gold_column_comments.sql
-- then re-run the OM Gold ingestion workflow.

-- ====================================================================== market
COMMENT ON TABLE market.city_metrics IS
  'Indicateurs marché par commune et année : prix DVF, revenu FiLoSoFi, population INSEE et indice d''accessibilité.';
COMMENT ON COLUMN market.city_metrics.code_commune IS 'Code INSEE commune (5 car., ex. 31555). Paris/Lyon/Marseille agrégés au niveau commune mère.';
COMMENT ON COLUMN market.city_metrics.year IS 'Année des transactions DVF (millésime de la ligne).';
COMMENT ON COLUMN market.city_metrics.nom_commune IS 'Nom officiel de la commune.';
COMMENT ON COLUMN market.city_metrics.code_departement IS 'Code département (2 ou 3 car., ex. 31, 2A, 971).';
COMMENT ON COLUMN market.city_metrics.region IS 'Nom de la région administrative.';
COMMENT ON COLUMN market.city_metrics.population IS 'Population municipale INSEE (recensement).';
COMMENT ON COLUMN market.city_metrics.insee_ref_year IS 'Millésime du recensement INSEE pour la population (transparence : peut différer de `year`).';
COMMENT ON COLUMN market.city_metrics.revenu_median IS 'Revenu médian disponible par UC (FiLoSoFi, MED_SL), en euros.';
COMMENT ON COLUMN market.city_metrics.revenu_ref_year IS 'Millésime FiLoSoFi du revenu médian.';
COMMENT ON COLUMN market.city_metrics.prix_m2_median IS 'Prix médian au m² des transactions de l''année (€/m²).';
COMMENT ON COLUMN market.city_metrics.prix_m2_mean IS 'Prix moyen au m² des transactions de l''année (€/m²).';
COMMENT ON COLUMN market.city_metrics.surface_median IS 'Surface bâtie médiane des biens vendus (m²).';
COMMENT ON COLUMN market.city_metrics.nb_transactions IS 'Nombre de mutations retenues pour le calcul (après nettoyage Silver).';
COMMENT ON COLUMN market.city_metrics.longitude IS 'Longitude du centroïde communal (WGS84).';
COMMENT ON COLUMN market.city_metrics.latitude IS 'Latitude du centroïde communal (WGS84).';
COMMENT ON COLUMN market.city_metrics.period_start IS 'Première date de mutation observée sur la période.';
COMMENT ON COLUMN market.city_metrics.period_end IS 'Dernière date de mutation observée sur la période.';
COMMENT ON COLUMN market.city_metrics.updated_at IS 'Horodatage de la dernière écriture Gold (UTC).';
COMMENT ON COLUMN market.city_metrics.type_commune IS 'Typologie de la commune (ex. urbaine/rurale) issue de l''enrichissement.';
COMMENT ON COLUMN market.city_metrics.affordability_years IS 'Indice d''accessibilité : années de revenu médian nécessaires pour acheter un bien de surface médiane.';
COMMENT ON COLUMN market.city_metrics.m2_par_an IS 'Surface (m²) achetable avec un an de revenu médian.';
COMMENT ON COLUMN market.city_metrics.affordability_class IS 'Classe d''accessibilité dérivée de affordability_years (ex. Abordable / Tendu / Très tendu).';

COMMENT ON TABLE market.arrondissement_metrics IS
  'Mêmes indicateurs que city_metrics mais au niveau arrondissement municipal (Paris/Lyon/Marseille), avec rattachement à la commune mère.';
COMMENT ON COLUMN market.arrondissement_metrics.code_arrondissement IS 'Code INSEE de l''arrondissement municipal (ex. 75101).';
COMMENT ON COLUMN market.arrondissement_metrics.year IS 'Année des transactions DVF.';
COMMENT ON COLUMN market.arrondissement_metrics.nom_arrondissement IS 'Nom de l''arrondissement.';
COMMENT ON COLUMN market.arrondissement_metrics.code_commune_parent IS 'Code INSEE de la commune mère (75056, 69123, 13055).';
COMMENT ON COLUMN market.arrondissement_metrics.nom_commune_parent IS 'Nom de la commune mère.';
COMMENT ON COLUMN market.arrondissement_metrics.code_departement IS 'Code département.';
COMMENT ON COLUMN market.arrondissement_metrics.region IS 'Nom de la région administrative.';
COMMENT ON COLUMN market.arrondissement_metrics.population IS 'Population municipale INSEE de l''arrondissement.';
COMMENT ON COLUMN market.arrondissement_metrics.insee_ref_year IS 'Millésime du recensement INSEE pour la population.';
COMMENT ON COLUMN market.arrondissement_metrics.revenu_median IS 'Revenu médian disponible par UC (FiLoSoFi), en euros.';
COMMENT ON COLUMN market.arrondissement_metrics.revenu_ref_year IS 'Millésime FiLoSoFi du revenu médian.';
COMMENT ON COLUMN market.arrondissement_metrics.prix_m2_median IS 'Prix médian au m² (€/m²).';
COMMENT ON COLUMN market.arrondissement_metrics.prix_m2_mean IS 'Prix moyen au m² (€/m²).';
COMMENT ON COLUMN market.arrondissement_metrics.surface_median IS 'Surface bâtie médiane (m²).';
COMMENT ON COLUMN market.arrondissement_metrics.nb_transactions IS 'Nombre de mutations retenues.';
COMMENT ON COLUMN market.arrondissement_metrics.longitude IS 'Longitude du centroïde (WGS84).';
COMMENT ON COLUMN market.arrondissement_metrics.latitude IS 'Latitude du centroïde (WGS84).';
COMMENT ON COLUMN market.arrondissement_metrics.period_start IS 'Première date de mutation sur la période.';
COMMENT ON COLUMN market.arrondissement_metrics.period_end IS 'Dernière date de mutation sur la période.';
COMMENT ON COLUMN market.arrondissement_metrics.updated_at IS 'Horodatage de la dernière écriture Gold (UTC).';
COMMENT ON COLUMN market.arrondissement_metrics.type_commune IS 'Typologie de la commune.';
COMMENT ON COLUMN market.arrondissement_metrics.affordability_years IS 'Années de revenu médian pour acheter un bien de surface médiane.';
COMMENT ON COLUMN market.arrondissement_metrics.m2_par_an IS 'Surface (m²) achetable avec un an de revenu médian.';
COMMENT ON COLUMN market.arrondissement_metrics.affordability_class IS 'Classe d''accessibilité.';

COMMENT ON TABLE market.city_price_trend IS
  'Série temporelle mensuelle du prix médian au m² par commune (pour les graphiques de tendance).';
COMMENT ON COLUMN market.city_price_trend.code_commune IS 'Code INSEE commune.';
COMMENT ON COLUMN market.city_price_trend.year IS 'Année de la mesure.';
COMMENT ON COLUMN market.city_price_trend.month IS 'Mois de la mesure (1-12).';
COMMENT ON COLUMN market.city_price_trend.prix_m2_median IS 'Prix médian au m² sur le mois (€/m²).';
COMMENT ON COLUMN market.city_price_trend.nb_transactions IS 'Nombre de mutations sur le mois.';

COMMENT ON TABLE market.housing_price_by_type IS
  'Prix médian au m² ventilé par type de bien (maison / appartement) et par commune.';
COMMENT ON COLUMN market.housing_price_by_type.code_commune IS 'Code INSEE commune.';
COMMENT ON COLUMN market.housing_price_by_type.type_local IS 'Type de bien (Maison, Appartement).';
COMMENT ON COLUMN market.housing_price_by_type.prix_m2_median IS 'Prix médian au m² pour ce type (€/m²).';
COMMENT ON COLUMN market.housing_price_by_type.surface_median IS 'Surface médiane pour ce type (m²).';
COMMENT ON COLUMN market.housing_price_by_type.nb_transactions IS 'Nombre de mutations pour ce type.';

-- ================================================================ demographics
COMMENT ON TABLE demographics.commune_profile IS
  'Profil démographique par commune (INSEE recensement) : population et répartition par âge / sexe.';
COMMENT ON COLUMN demographics.commune_profile.code_commune IS 'Code INSEE commune.';
COMMENT ON COLUMN demographics.commune_profile.year IS 'Millésime du recensement INSEE.';
COMMENT ON COLUMN demographics.commune_profile.population_total IS 'Population municipale totale.';
COMMENT ON COLUMN demographics.commune_profile.pct_moins25 IS 'Part de la population de moins de 25 ans (%).';
COMMENT ON COLUMN demographics.commune_profile.pct_25_64 IS 'Part de la population de 25 à 64 ans (%).';
COMMENT ON COLUMN demographics.commune_profile.pct_65plus IS 'Part de la population de 65 ans et plus (%).';
COMMENT ON COLUMN demographics.commune_profile.part_femmes IS 'Part de femmes dans la population (%).';
COMMENT ON COLUMN demographics.commune_profile.updated_at IS 'Horodatage de la dernière écriture Gold (UTC).';

-- ==================================================================== mobility
COMMENT ON TABLE mobility.commune_transport IS
  'Desserte ferroviaire par commune (SNCF) : nombre de gares, fréquentation, classe de desserte et distance à la gare la plus proche.';
COMMENT ON COLUMN mobility.commune_transport.code_commune IS 'Code INSEE commune.';
COMMENT ON COLUMN mobility.commune_transport.nb_gares IS 'Nombre de gares de voyageurs situées dans la commune.';
COMMENT ON COLUMN mobility.commune_transport.frequentation_totale IS 'Fréquentation annuelle cumulée des gares de la commune (voyageurs + non-voyageurs).';
COMMENT ON COLUMN mobility.commune_transport.frequentation_year IS 'Année de référence de la fréquentation SNCF.';
COMMENT ON COLUMN mobility.commune_transport.best_segment_drg IS 'Meilleur segment DRG SNCF parmi les gares de la commune (a/b/c).';
COMMENT ON COLUMN mobility.commune_transport.desserte_class IS 'Classe de desserte dérivée : Hub majeur / Bien desservie / Desservie / Non desservie.';
COMMENT ON COLUMN mobility.commune_transport.updated_at IS 'Horodatage de la dernière écriture Gold (UTC).';
COMMENT ON COLUMN mobility.commune_transport.distance_gare_km IS 'Distance haversine (km) au centroïde de la commune jusqu''à la gare la plus proche (plafonnée à 150 km).';
COMMENT ON COLUMN mobility.commune_transport.gare_proche_uic IS 'Code UIC de la gare la plus proche.';
COMMENT ON COLUMN mobility.commune_transport.gare_proche_nom IS 'Nom de la gare la plus proche.';

COMMENT ON TABLE mobility.gares IS
  'Référentiel des gares de voyageurs SNCF géolocalisées, avec fréquentation et rattachement communal.';
COMMENT ON COLUMN mobility.gares.code_uic IS 'Code UIC de la gare (identifiant unique ; premier UIC si la gare en porte plusieurs).';
COMMENT ON COLUMN mobility.gares.nom_gare IS 'Nom de la gare.';
COMMENT ON COLUMN mobility.gares.code_commune IS 'Code INSEE de la commune d''implantation.';
COMMENT ON COLUMN mobility.gares.segment_drg IS 'Segment DRG SNCF de la gare (a = grande, b = moyenne, c = petite).';
COMMENT ON COLUMN mobility.gares.frequentation IS 'Fréquentation annuelle de la gare.';
COMMENT ON COLUMN mobility.gares.frequentation_year IS 'Année de référence de la fréquentation.';
COMMENT ON COLUMN mobility.gares.longitude IS 'Longitude de la gare (WGS84).';
COMMENT ON COLUMN mobility.gares.latitude IS 'Latitude de la gare (WGS84).';
COMMENT ON COLUMN mobility.gares.updated_at IS 'Horodatage de la dernière écriture Gold (UTC).';

-- ==================================================================== services
COMMENT ON TABLE services.commune_equipements IS
  'Équipements et services par commune (INSEE BPE) : comptes par domaine, aménités clés et niveau d''équipement.';
COMMENT ON COLUMN services.commune_equipements.code_commune IS 'Code INSEE commune.';
COMMENT ON COLUMN services.commune_equipements.year IS 'Millésime de la Base Permanente des Équipements (BPE).';
COMMENT ON COLUMN services.commune_equipements.nb_services IS 'Nombre d''équipements du domaine Services aux particuliers (A).';
COMMENT ON COLUMN services.commune_equipements.nb_commerces IS 'Nombre d''équipements du domaine Commerces (B).';
COMMENT ON COLUMN services.commune_equipements.nb_enseignement IS 'Nombre d''équipements du domaine Enseignement (C).';
COMMENT ON COLUMN services.commune_equipements.nb_sante IS 'Nombre d''équipements du domaine Santé / action sociale (D).';
COMMENT ON COLUMN services.commune_equipements.nb_transport IS 'Nombre d''équipements du domaine Transports / déplacements (E).';
COMMENT ON COLUMN services.commune_equipements.nb_sport_culture IS 'Nombre d''équipements du domaine Sports / loisirs / culture (F).';
COMMENT ON COLUMN services.commune_equipements.nb_tourisme IS 'Nombre d''équipements du domaine Tourisme (G).';
COMMENT ON COLUMN services.commune_equipements.nb_total IS 'Nombre total d''équipements tous domaines confondus.';
COMMENT ON COLUMN services.commune_equipements.nb_medecin IS 'Nombre de médecins généralistes (BPE D265).';
COMMENT ON COLUMN services.commune_equipements.nb_pharmacie IS 'Nombre de pharmacies (BPE D307).';
COMMENT ON COLUMN services.commune_equipements.nb_ecole IS 'Nombre d''écoles élémentaires (BPE C107/C108/C109).';
COMMENT ON COLUMN services.commune_equipements.nb_supermarche IS 'Nombre de supermarchés / hypermarchés (BPE B104/B105).';
COMMENT ON COLUMN services.commune_equipements.nb_boulangerie IS 'Nombre de boulangeries (BPE B207).';
COMMENT ON COLUMN services.commune_equipements.niveau_equipement IS 'Niveau d''équipement de la commune : Sous-équipée / Équipée / Bien équipée / Très équipée.';
COMMENT ON COLUMN services.commune_equipements.updated_at IS 'Horodatage de la dernière écriture Gold (UTC).';
