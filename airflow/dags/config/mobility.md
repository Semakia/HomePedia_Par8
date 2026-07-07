# mobility_etl — accessibilité ferroviaire (SNCF)

Pipeline de tratitement des données concernant la desserte train par commune.

**Source :** open data SNCF (`gares-de-voyageurs` + `frequentation-gares`).

**Étapes**
1. `ingest_sncf` — récupère les jeux SNCF vers S3 (Bronze). *(host-side)*
2. `bronze_to_silver_sncf` — nettoyage Spark → une ligne par gare (Silver).
3. `mobility_to_gold` — agrégation → schéma Gold `mobility`
   (`mobility.gares` + `mobility.commune_transport`).
4. `quality_check` — porte qualité sur le Gold servi (JDBC).

**Planning :** mensuel, le 1er à 04:00 (`0 4 1 * *`) — décalé après `housing`
pour ne pas se disputer la VM Spark.

> Spark tourne sur la VM GCP on-demand (démarrée/soumise/éteinte par le DAG).
