Contenu de silver
 12 objets, ~2,3 Mo au total (compressé snappy)
3 partitions : départements 13 (Marseille), 69 (Lyon), 75 (Paris), millésime 2024
4 fichiers part-… par partition (= 4 partitions Spark écrites en parallèle par le local[*])
63 000 lignes au total (le dernier run DAG a réécrit 75 et 69 + ajouté 13)

Schéma de chaque ligne (1 bien résidentiel vendu)
id_mutation, date_mutation, year, month, code_commune, code_departement, nom_commune, type_local, surface_reelle_bati, nombre_pieces_principales, valeur_fonciere, prix_m2, longitude, latitude

À noter
Pas de _SUCCESS : le committer S3A ne l'a pas écrit (config par défaut). Sans impact — les données sont lisibles (on a relu 63 000 lignes). On pourra activer le marqueur plus tard si on veut un signal de complétude propre.
year et code_departement ne sont pas des colonnes dans les fichiers : ce sont les clés de partition (encodées dans le chemin), comme attendu en Parquet partitionné. Spark les reconstruit à la lecture.
Les 4 part-files par partition viennent du parallélisme local[*]. Pour des partitions plus volumineuses on pourra coalesce/repartition afin d'éviter les petits fichiers, mais à 2,3 Mo c'est sans enjeu.