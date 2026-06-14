# ADR — PostgreSQL plutôt que ClickHouse pour la couche Gold (serving)

- **Statut** : Accepté
- **Date** : 2026-06-12
- **Périmètre** : couche **Gold** de HOMEPEDIA (base servie par l'API FastAPI)
- **Décision** : conserver **PostgreSQL** comme moteur de la couche Gold. Ne **pas**
  introduire ClickHouse à ce stade. Réévaluer si les déclencheurs listés en
  section 8 se présentent.

---

## 1. Contexte

HOMEPEDIA suit une architecture **médaillon** (Bronze → Silver → Gold) :

- **Bronze / Silver** : données brutes puis nettoyées, en **Parquet sur S3**
  (volume : DVF ≈ 4,6 M lignes/an × plusieurs millésimes, + INSEE, + FiLoSoFi).
- **Gold** : tables **pré-agrégées** servies par l'API. Aujourd'hui dans
  **PostgreSQL** :
  - `city_metrics` (1 ligne par commune × année),
  - `city_price_trend` (tendance mensuelle),
  - `housing_price_by_type` (prix par type de bien).
  - Volume Gold actuel : **≈ 88 000 lignes** sur `city_metrics`.

La question posée : *un moteur colonnaire comme **ClickHouse** serait-il plus
pertinent pour ce projet ?*

Cet ADR tranche en partant du **besoin réel** (le workload), pas de la mode
technologique.

---

## 2. Les deux candidats en une phrase

| | PostgreSQL | ClickHouse |
|---|---|---|
| Famille | **Row-store OLTP** (transactionnel) | **Colonnaire OLAP** (analytique) |
| Optimisé pour | lectures/écritures **ponctuelles**, indexées, transactions, forte concurrence | **agréger massivement** des colonnes (millions/milliards de lignes) |
| Mauvais sur | agrégats lourds sur de très gros volumes | lookups ligne-à-ligne, **forte concurrence de petites requêtes**, updates fréquents |

> Point clé : ce ne sont pas des concurrents directs, ce sont des outils
> **optimisés pour des usages opposés**. Le bon choix dépend du **profil de
> requêtes** de la couche concernée.

---

## 3. Le workload réel de la couche Gold

La couche Gold est interrogée **exclusivement par l'API**, dont les requêtes
sont :

1. **Lookups ponctuels** : `GET /cities/{code}` → « la fiche de la commune
   01053 ». Une ligne, par clé primaire.
2. **Listes filtrées / triées / paginées** : `GET /cities?sort=population` →
   quelques dizaines de lignes parmi 88 000, avec `WHERE`/`ORDER BY`/`LIMIT`.
3. **Forte concurrence de petites requêtes** : un front web = beaucoup
   d'utilisateurs, chacun déclenchant de nombreuses requêtes **courtes**.
4. **Données déjà pré-agrégées** : le gros du calcul (médianes, tendances) est
   fait **en amont** par le job Spark `silver_to_gold`. L'API ne *calcule* quasi
   rien, elle **lit** des résultats prêts.

**C'est le profil OLTP type.** Pas d'agrégation lourde au moment de la requête,
volume modeste, beaucoup de petites lectures concurrentes, des lookups indexés.

C'est **exactement** ce pour quoi PostgreSQL est conçu — et **exactement** ce sur
quoi ClickHouse n'apporte rien (voire est moins adapté, cf. section 5).

---

## 4. Critères de décision

| Critère | PostgreSQL | ClickHouse | Gagnant pour HOMEPEDIA |
|---|---|---|---|
| Lookup d'une ligne par clé | ⚡ excellent (index B-tree) | 😐 correct, pas son fort | **Postgres** |
| Petites requêtes très concurrentes (API web) | ✅ conçu pour | ⚠️ pensé pour peu de grosses requêtes | **Postgres** |
| Agrégats lourds sur données brutes | 🐢 lent | ⚡ excellent | ClickHouse *(non requis ici)* |
| Volume Gold actuel (~88k lignes) | ✅ instantané | ✅ instantané (surdimensionné) | **Postgres** (suffit) |
| Transactions / cohérence (ACID) | ✅ natif | ❌ limité | **Postgres** |
| Updates / corrections de lignes | ✅ natif | ❌ append-oriented | **Postgres** |
| Écriture depuis Spark (JDBC) | ✅ driver mûr, déjà intégré | ✅ possible | **Postgres** (déjà en place) |
| Intégration FastAPI / SQLAlchemy | ✅ standard, psycopg2 | ⚠️ driver tiers, SQL non standard | **Postgres** |
| Coût (open source, auto-hébergé) | ✅ gratuit | ✅ gratuit | égalité |
| Empreinte mémoire (dev local 8 Go) | légère | plus gourmand (service permanent) | **Postgres** |
| Maturité écosystème serving (ORM, migrations, BI) | ✅ immense | analytique surtout | **Postgres** |

**Bilan : Postgres l'emporte sur tous les critères qui comptent pour le serving
de la couche Gold.** ClickHouse ne gagne que sur l'agrégation massive — un besoin
**absent** de la couche Gold (le pré-calcul est déjà fait en Silver→Gold).

---

## 5. Pourquoi ClickHouse serait même contre-productif ici

1. **Profil de requêtes inadapté.** ClickHouse est optimisé pour **peu de
   requêtes lourdes** (scans analytiques), pas pour **beaucoup de requêtes
   courtes concurrentes** comme une API web. Chaque requête a un coût fixe
   d'orchestration ; sur des milliers de petits lookups, ce n'est pas son terrain.

2. **Pas de gain de perf à ce volume.** Le Gold fait ~88k lignes : Postgres y
   répond en **quelques millisecondes**. Il n'y a **aucune lenteur à corriger**.
   Remplacer un moteur pour résoudre un problème inexistant = sur-engineering.

3. **Perte de fonctionnalités transactionnelles.** L'API et l'ETL bénéficient des
   garanties ACID, des contraintes (PK), des `UPDATE` ciblés (ex. backfill du
   millésime `insee_ref_year`). ClickHouse, append-oriented, complique ces
   opérations.

4. **Friction d'intégration.** Tout l'écosystème serving (SQLAlchemy Core,
   psycopg2, migrations SQL, le driver JDBC déjà *baké* dans l'image Spark) est
   pensé pour Postgres. ClickHouse imposerait un dialecte SQL différent et des
   drivers tiers, pour zéro bénéfice côté serving.

5. **Coût opérationnel.** ClickHouse est un **service serveur permanent** de plus,
   plus gourmand en RAM — un poids non négligeable sur un environnement de dev
   contraint (8 Go, déjà partagé entre Spark, Airflow, MinIO, Postgres).

> À noter : le dernier incident vécu (base Gold injoignable) était un problème
> **réseau** (VPS distant coupé), **pas** de lenteur de requêtage. ClickHouse n'y
> aurait rien changé : un serveur injoignable l'est quel que soit le moteur.

---

## 6. Pourquoi PostgreSQL est le bon choix

- **Adéquation au workload** : lookups indexés + petites requêtes concurrentes =
  cœur de métier d'un row-store OLTP.
- **Suffisant à l'échelle** : 88k lignes pré-agrégées → réponses
  quasi-instantanées, sans tuning particulier.
- **Le pré-calcul est déjà fait** : la couche Gold matérialise les agrégats
  (pattern **data marts / Kimball**) via Spark. La base n'a donc **pas** besoin
  d'être un moteur d'agrégation : elle sert des résultats prêts.
- **Robustesse & simplicité** : ACID, contraintes, `UPDATE`/`TRUNCATE`, un seul
  moteur bien connu, écosystème immense.
- **Déjà intégré de bout en bout** : Spark écrit en JDBC (truncate + reload),
  l'API lit via SQLAlchemy/psycopg2, le schéma est versionné en SQL.
- **Évolutif si besoin** : `+ Redis` (cache des vues chaudes) déjà prévu pour
  encaisser la montée en charge **avant** d'envisager un changement de moteur.

---

## 7. Le bon endroit pour un colonnaire (s'il en faut un)

Le découpage en petites tables pré-agrégées (le « split ») est un choix
**délibéré et adapté au serving**, pas une dette. Un moteur colonnaire ne se
justifie **pas** pour servir la couche Gold.

En revanche, il aurait un sens **en complément**, pour un **autre besoin** :
l'**exploration ad hoc de la couche Silver granulaire** (4,6 M lignes/an), où l'on
voudrait interroger n'importe quel axe **sans pré-agréger**. Dans ce cas :

- **DuckDB** (recommandé pour un POC) : OLAP **embarqué**, lit le **Parquet S3
  directement**, **zéro infrastructure** (une simple lib), idéal pour de
  l'analyse exploratoire. Aucun serveur permanent à maintenir.
- **ClickHouse** : seulement si ce besoin exploratoire devient **récurrent, à
  fort volume et multi-utilisateurs** au point de justifier un vrai serveur
  colonnaire.

> Principe directeur : **« right tool, right layer »**. Postgres pour **servir**
> le Gold ; un colonnaire éventuellement pour **explorer** le Silver — jamais
> l'un à la place de l'autre.

---

## 8. Quand réévaluer cette décision

Rouvrir cet ADR si **l'un** de ces déclencheurs apparaît :

1. Le volume **servi** par l'API passe de ~88k lignes à **plusieurs millions/
   dizaines de millions**, au point que les `WHERE`/`ORDER BY` ralentissent
   malgré les index et Redis.
2. Le besoin produit évolue vers des **agrégations à la volée sur le granulaire**
   (filtres arbitraires : type × année × tranche de surface × rayon
   géographique…), impossibles à pré-matérialiser raisonnablement.
3. Une **forte volumétrie d'analyse interactive multi-utilisateurs** émerge
   (dashboards exploratoires), au-delà de ce que Postgres + Redis encaissent.

Tant qu'aucun de ces déclencheurs n'est atteint, **PostgreSQL reste le choix
pertinent** pour la couche Gold de HOMEPEDIA.

---

## 9. Résumé en une phrase

> Le besoin de la couche Gold est du **serving OLTP** (petits lookups indexés,
> forte concurrence, données déjà pré-agrégées, ~88k lignes) : c'est le cœur de
> métier de **PostgreSQL**. ClickHouse répond à un problème — l'agrégation
> massive à la volée — que **ce projet n'a pas** au niveau servi. On garde
> Postgres, et on réservera un colonnaire (DuckDB d'abord) à l'exploration du
> Silver si ce besoin émerge.
