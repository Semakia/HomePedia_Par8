# ADR — Parquet sur S3 pour la couche Silver (plutôt qu'une base de données)

- **Statut** : Accepté
- **Date** : 2026-06-12
- **Périmètre** : couche **Silver** de HOMEPEDIA (données nettoyées,
  intermédiaires, consommées par Spark)
- **Décision** : stocker la couche Silver en **fichiers Parquet partitionnés sur
  S3**, et **non** dans une base de données. Réévaluer vers un **format de table**
  (Iceberg / Delta / Hudi) — pas vers une base — si les déclencheurs de la
  section 8 apparaissent.

---

## 1. Contexte

HOMEPEDIA suit une architecture **médaillon** (Bronze → Silver → Gold) :

- **Bronze** : données brutes, intactes, déposées telles quelles sur S3
  (CSV/JSON gzippés + manifeste de provenance).
- **Silver** : données **nettoyées, typées, dédoublonnées**. C'est ici qu'on
  applique la logique métier (ex. filtre **mono-bien** DVF). Volume important :
  DVF ≈ **4,6 M lignes/an** × plusieurs millésimes, + INSEE, + FiLoSoFi.
- **Gold** : agrégats pré-calculés servis par l'API (dans **PostgreSQL** —
  cf. [postgres_vs_clickhouse.md](postgres_vs_clickhouse.md)).

La couche Silver est aujourd'hui en **Parquet partitionné sur S3**
(`s3://homepedia-silver/dvf`, `/insee`, `/filosofi`), partitionnée par `year` et
`code_departement`. La question : *fallait-il une base de données pour le Silver
plutôt que des fichiers ?*

---

## 2. Les deux options en une phrase

| | Parquet sur S3 | Base de données (relationnelle) |
|---|---|---|
| Nature | **Fichiers colonnaires** sur stockage objet | **Serveur** qui stocke et sert la donnée |
| Lu par | moteurs de calcul (Spark, DuckDB, Athena…) | applications via connexions SQL |
| Optimisé pour | **scans analytiques massifs**, débit | requêtes ponctuelles, transactions, concurrence |
| Stockage / calcul | **découplés** (le stockage ne tourne pas) | **couplés** (le serveur est le goulot) |

> Comme pour le Gold, le bon choix dépend du **profil d'accès** de la couche —
> pas d'une préférence dogmatique.

---

## 3. Le workload réel de la couche Silver

Qui lit le Silver, et comment ?

1. **Spark, en batch.** Le Silver est consommé par des jobs Spark
   (`silver_to_gold`, qualité) qui **scannent et agrègent des millions de lignes
   d'un coup**. Profil **OLAP pur**.
2. **Jamais d'accès ponctuel humain.** Personne ne fait « donne-moi la ligne X »
   sur le Silver. Ce n'est pas une couche servie à des utilisateurs.
3. **Reprocessing par tranches.** On rejoue un **millésime entier** (ex. Silver
   DVF 2023) sans toucher aux autres.
4. **Écriture en parallèle, en masse.** Spark produit beaucoup de fichiers en
   parallèle (des centaines de milliers de lignes), pas des `INSERT` un par un.

C'est le profil **analytique batch, gros volume, écriture en masse, sans
transactionnel** — exactement ce pour quoi Parquet/S3 est fait, et exactement ce
sur quoi une base relationnelle serait inadaptée et coûteuse.

---

## 4. Critères de décision

| Critère | Parquet sur S3 | Base de données | Gagnant |
|---|---|---|---|
| Lecture analytique (scan de colonnes) | ⚡ colonnaire : lit *les colonnes utiles* | 🐢 row-store : lit toutes les lignes | **Parquet** |
| Découplage stockage / calcul | ✅ total (Spark allumé à la demande) | ❌ serveur permanent = goulot | **Parquet** |
| Partitionnement (pruning + overwrite ciblé) | ✅ natif par dossier | ⚠️ possible mais plus lourd | **Parquet** |
| Coût de stockage (gros volume) | ✅ objet, compressé, quelques centimes/Go | ❌ stockage serveur cher | **Parquet** |
| Débit d'écriture depuis Spark | ✅ parallèle, fichiers | 🐢 bulk-load lent, par connexion | **Parquet** |
| Format ouvert / interopérable | ✅ Spark, DuckDB, Athena, pandas, Trino | ❌ enfermé dans le moteur | **Parquet** |
| Reproductibilité / idempotence | ✅ immuable, overwrite de partition | ⚠️ état mutable, transactions à gérer | **Parquet** |
| Évolution de schéma | ✅ souple (schema-on-read) | ⚠️ migrations | **Parquet** |
| Transactions ACID / upserts | ❌ non (fichiers bruts) | ✅ natif | Base *(non requis ici)* |
| Lookup ponctuel indexé | ❌ pas le but | ✅ | Base *(non requis ici)* |

**Bilan : Parquet/S3 gagne sur tous les critères qui comptent pour une couche
intermédiaire analytique.** La base ne gagne que sur l'ACID et les lookups —
deux besoins **absents** du Silver (ils existent au Gold, d'où Postgres là-bas).

---

## 5. Pourquoi une base de données serait un mauvais choix pour le Silver

1. **Inefficacité de lecture.** Calculer une médiane de prix/m² = lire **une
   colonne**. Un row-store lit **toutes les lignes entières** pour n'en garder
   qu'une colonne. Le colonnaire (Parquet) lit juste ce qu'il faut → ordres de
   grandeur plus rapide sur les agrégats massifs.

2. **Le serveur devient le goulot.** Avec une base, **tout passe par le serveur**
   (RAM, connexions, tuning). Charger 4,6 M lignes/an × N millésimes × 4 sources
   dedans = lent et douloureux. Avec Parquet, le stockage **ne tourne pas** ; le
   calcul (Spark) lit en parallèle et s'éteint.

3. **Coût injustifié.** Le Silver est le **gros volume intermédiaire** que
   **personne n'interroge directement**. Le mettre dans une base = payer un
   stockage serveur cher + index à maintenir pour de la donnée transitoire.

4. **Perte de la rejouabilité simple.** Un Parquet est **immuable** : on
   reconstruit depuis le Bronze, on écrase la partition, fini. Dans une base, il
   faut gérer `TRUNCATE`/`DELETE`/transactions, l'état mute — plus fragile pour
   une couche qu'on veut **jetable et reconstructible**.

---

## 6. Pourquoi Parquet/S3 est le bon choix

- **Colonnaire = lecture analytique optimale** pour le seul consommateur (Spark).
- **Découplage stockage/calcul** : le volume vit sur S3 (objet, pas cher,
  scalable) ; le calcul est éphémère.
- **Partitionnement `year`/`code_departement`** → deux bénéfices concrets, déjà
  exploités :
  - **partition pruning** : le Gold qui ne veut que 2024 lit `year=2024/` et
    ignore physiquement le reste ;
  - **dynamic partition overwrite** (`spark.sql.sources.partitionOverwriteMode=
    dynamic`) : rejouer le Silver d'une seule année **n'écrase que ce dossier** —
    c'est ce qui a permis de backfiller 2021→2025 année par année sans toucher
    aux autres.
- **Compression forte** (colonnaire) → stockage minimal.
- **Format ouvert** : lisible par Spark, **DuckDB**, **Athena**, pandas, Trino →
  zéro lock-in, exploration ad hoc possible sans Spark.
- **Reproductibilité** : couplé au Bronze rejouable, c'est l'assurance-vie du
  pipeline. *(Vécu : quand des jobs Silver ont planté (DNS), aucune donnée
  perdue — le Bronze était là, on a juste relancé le Silver.)*
- **Portabilité** : bascule **MinIO ⇄ AWS S3** par une simple variable d'env
  (`S3_ENDPOINT_URL`) — dev local = prod, sans changer une ligne de code.

---

## 7. Les contreparties (assumées) de Parquet/S3

Aucun choix n'est gratuit. Ce que Parquet/S3 **ne** donne **pas**, et pourquoi ce
n'est pas un problème ici :

- **Pas d'ACID / pas d'upsert ligne-à-ligne.** Non requis : on reconstruit des
  partitions entières, on ne corrige pas des lignes individuelles.
- **Pas d'index / pas de lookup ponctuel.** Non requis : le Silver n'est jamais
  interrogé à la ligne ; c'est le rôle du Gold (Postgres).
- **« Small files problem ».** Trop de petits fichiers nuisent aux perfs ;
  maîtrisé par le partitionnement et le contrôle du nombre de partitions de
  sortie (ex. `spark.sql.shuffle.partitions`).
- **Cohérence.** S3 est désormais *strongly consistent* en lecture-après-écriture,
  ce qui lève l'ancien risque des committers S3A.

---

## 8. Quand réévaluer cette décision

Le bon réflexe si les besoins évoluent n'est **pas** de passer à une base, mais
d'adopter un **format de table** par-dessus le Parquet/S3 (**Apache Iceberg**,
**Delta Lake** ou **Hudi**), qui ajoute ACID, upserts, *time-travel* et
*schema enforcement* **tout en gardant** le découplage stockage/calcul et le
format ouvert.

Déclencheurs pour cette évolution :

1. Besoin d'**upserts / corrections fines** (CDC, MAJ ligne-à-ligne) plutôt que
   de réécrire des partitions entières.
2. Besoin d'**ACID multi-écrivains** (plusieurs jobs écrivant la même table
   simultanément, sans corruption).
3. Besoin de **time-travel / versionnement** (requêter l'état d'hier, rollback).
4. **Small files** devenant ingérable à grande échelle (compaction automatique
   souhaitée).

> Le passage à une **vraie base de données** pour le Silver, lui, n'est **jamais**
> la bonne réponse : il casserait le découplage stockage/calcul qui fait la valeur
> de la couche.

---

## 9. Résumé en une phrase

> Le Silver est une couche **analytique batch, gros volume, écrite en masse par
> Spark et jamais interrogée à la ligne** : c'est le terrain idéal du **Parquet
> colonnaire partitionné sur S3** (lecture efficace, stockage/calcul découplés,
> coût minimal, rejouable, format ouvert). Une base de données y serait lente,
> chère et fragile. Si des besoins transactionnels émergent, on évolue vers un
> **format de table** (Iceberg/Delta) — pas vers une base.
