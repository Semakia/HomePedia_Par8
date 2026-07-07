# housing_etl — pipeline principal HOMEPEDIA

Pipeline batch de traitement des données du logement et du contexte socio-démographique.

**Sources ingérées → S3 (Bronze) :** DVF (transactions immobilières), INSEE
(population + démographie), FiLoSoFi (revenus).

**Étapes**
1. `ingest_*` — récupère DVF / INSEE / FiLoSoFi vers S3 (Bronze).
2. `bronze_to_silver_*` — nettoyage Spark → Parquet Silver (par an).
3. `silver_to_gold` — jointure DVF × INSEE × FiLoSoFi → tables Gold (schéma `market`).
4. `quality_*` — portes qualité sur Silver et sur le Gold servi (JDBC).

**Planning :** mensuel, le 1er à 00:00 (`0 0 1 * *`).

**Config de run** (facultatif) : `{ "year": 2024, "departements": ["75", "69"] }`.
Sans `departements`, tous les codes de `utils/departements.json` sont traités.

> Spark tourne sur la VM GCP on-demand : le DAG démarre la VM, soumet les
> `spark-submit` par SSH, puis l'éteint (`stop_spark_vm`, `trigger_rule=all_done`).
