# amenities_etl — équipements & services (INSEE BPE)

Pipeline **Bronze → Silver → Gold** des équipements locaux par commune.

**Source :** INSEE BPE (Base Permanente des Équipements).

**Étapes**
1. `ingest_bpe` — récupère la BPE vers S3 (Bronze). *(host-side)*
2. `bronze_to_silver_bpe` — nettoyage Spark → une ligne par commune × type
   d'équipement (Silver).
3. `services_to_gold` — pivot → schéma Gold `services`
   (`services.commune_equipements` : comptes par domaine + équipements clés + niveau).
4. `quality_check` — porte qualité sur le Gold servi (JDBC).

**Planning :** mensuel, le 1er à 06:00 (`0 6 1 * *`) — décalé après `mobility`
pour ne pas se disputer la VM Spark.

> Spark tourne sur la VM GCP on-demand (démarrée/soumise/éteinte par le DAG).
