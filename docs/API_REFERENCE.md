# HOMEPEDIA — Référence de l'API (pour le front)

Cette API sert la couche **Gold** de HOMEPEDIA : prix immobiliers, démographie,
accessibilité financière, transport et services, agrégés **par commune**. Ce
document est le **contrat complet** pour développer le front : endpoints,
paramètres, schémas de réponse et **vocabulaires** (enums) à afficher.

> Docs interactives auto-générées (toujours à jour) :
> - **Swagger UI** : `GET /docs` — tester chaque endpoint dans le navigateur.
> - **ReDoc** : `GET /redoc`.
> - **OpenAPI JSON** (pour générer un client TypeScript) : `GET /openapi.json`.

---

## 1. Généralités

| | |
|---|---|
| **Base URL (dev)** | `http://localhost:8000` |
| **Préfixe** | tous les endpoints métier sous **`/api/v1`** |
| **Format** | JSON (UTF-8). Pas d'auth pour l'instant. |
| **CORS** | autorisé pour `http://localhost:3000` et `http://localhost:8501` (configurable via `API_CORS_ORIGINS`) |
| **Méthodes** | `GET` uniquement (lecture seule) |

### Codes de statut
- `200` OK.
- `404` ressource inconnue (ex. commune inexistante sur `/cities/{code}`).
- `422` paramètre invalide (FastAPI renvoie le détail de validation).

### Conventions transverses
- **Identifiant commune** = `code_commune` = **code INSEE** (5 caractères, ex.
  `31555`, Corse `2A004`). C'est la clé de jointure partout.
- **Paris / Lyon / Marseille** sont **roulés** vers la commune mère
  (`75056` / `69123` / `13055`). Leurs arrondissements sont accessibles via
  l'endpoint dédié `/cities/{code}/arrondissements`.
- **`null`** = donnée non disponible (ex. commune hors référentiel INSEE, ou
  bloc non encore croisé). Toujours gérer le `null` côté front.
- **Millésimes** : chaque source a son année de référence (exposée). Voir §6.

---

## 2. Endpoints — vue d'ensemble

| Méthode & chemin | Réponse | Usage front |
|------------------|---------|-------------|
| `GET /health` | `{status, service, env}` | sonde de vie |
| `GET /ready` | `{status, components}` | sonde de connectivité (BDD/cache/S3) |
| `GET /api/v1/cities` | `Page<CityMetrics>` | **liste / carte / recherche / classement** |
| `GET /api/v1/cities/{code}` | `CityDetail` | **fiche ville complète** (5 axes) |
| `GET /api/v1/cities/{code}/arrondissements` | `Arrondissement[]` | drill-down Paris/Lyon/Marseille |
| `GET /api/v1/cities/{code}/gares` | `Gare[]` | gares de la commune (carte/détail) |
| `GET /api/v1/housing/prices` | `Page<HousingPriceByType>` | prix par type de bien (Maison/Appartement) |

---

## 3. Endpoints — détail

### 3.1 `GET /api/v1/cities` — liste des villes

Retourne une page de communes, chacune sur **son millésime le plus récent**
(headline). Idéal pour la carte, les classements et la recherche.

**Query params**

| Param | Type | Défaut | Description |
|-------|------|--------|-------------|
| `departement` | string | – | filtre exact sur le code département (`75`, `2A`, `971`) |
| `q` | string | – | recherche par nom, insensible à la casse |
| `sort` | string | `prix_m2_median` | tri ∈ `prix_m2_median`, `nb_transactions`, `population`, `nom_commune` |
| `order` | string | `desc` | `asc` \| `desc` |
| `page` | int ≥1 | `1` | numéro de page |
| `size` | int 1–200 | `50` | taille de page |

**Réponse** : `Page<CityMetrics>` (voir §4 pour l'enveloppe et §5 pour `CityMetrics`).
Tri `NULLS LAST` (les communes sans la métrique passent en fin).

```http
GET /api/v1/cities?sort=population&order=desc&size=3
GET /api/v1/cities?departement=69&sort=prix_m2_median&order=asc
GET /api/v1/cities?q=bourg&size=20
```

### 3.2 `GET /api/v1/cities/{code_commune}` — fiche ville

La **vue 360°** d'une commune. Renvoie `CityMetrics` (headline) **+** 5 blocs :
historique annuel, tendance mensuelle, démographie, transport, services.
`404` si la commune n'existe pas. Voir §5 `CityDetail`.

```http
GET /api/v1/cities/31555
```
### 3.3 `GET /api/v1/cities/{code_commune}/arrondissements`

Liste des **arrondissements municipaux** (Paris/Lyon/Marseille), chacun sur son
millésime récent. **Liste vide `[]`** pour toute autre commune. Voir
`Arrondissement` (§5).

```http
GET /api/v1/cities/75056/arrondissements
```

### 3.4 `GET /api/v1/cities/{code_commune}/gares`

Les **gares SNCF** de la commune, triées par fréquentation décroissante.
**Liste vide** si la commune n'a pas de gare. Voir `Gare` (§5).

```http
GET /api/v1/cities/75056/gares
```

### 3.5 `GET /api/v1/housing/prices` — prix par type de bien

**Query params** : `code_commune` (string, optionnel), `type_local`
(`Maison` | `Appartement`, optionnel), `page`, `size`.
**Réponse** : `Page<HousingPriceByType>`.

```http
GET /api/v1/housing/prices?code_commune=31555
```

---

## 4. Enveloppe paginée — `Page<T>`

```jsonc
{
  "items": [ /* T[] */ ],
  "total": 32448,   // nb total d'éléments correspondant au filtre
  "page": 1,        // page courante
  "size": 50,       // taille de page demandée
  "pages": 649      // nb total de pages = ceil(total / size)
}
```

---

## 5. Schémas de réponse (champs détaillés)

### `CityMetrics` (item de liste + base de la fiche)

| Champ | Type | Source | Sens |
|-------|------|--------|------|
| `code_commune` | string | INSEE | code commune (clé) |
| `year` | int? | DVF | millésime des prix (headline = + récent) |
| `nom_commune` | string | INSEE/DVF | nom |
| `code_departement` | string | INSEE | code département |
| `region` | string? | INSEE | nom de région |
| `population` | int? | INSEE | population (millésime `insee_ref_year`) |
| `insee_ref_year` | int? | INSEE | millésime population (ex. 2022) |
| `type_commune` | string? | dérivé | **typologie** (voir enum §6) |
| `revenu_median` | float? | FiLoSoFi | niveau de vie médian €/an |
| `revenu_ref_year` | int? | FiLoSoFi | millésime revenu (ex. 2023) |
| `affordability_years` | float? | dérivé | années de revenu pour 70 m² |
| `m2_par_an` | float? | dérivé | m² pour 1 an de revenu |
| `affordability_class` | string? | dérivé | **classe d'accessibilité** (enum §6) |
| `prix_m2_median` | float? | DVF | prix m² médian |
| `prix_m2_mean` | float? | DVF | prix m² moyen |
| `surface_median` | float? | DVF | surface médiane (m²) |
| `nb_transactions` | int | DVF | nb de ventes |
| `longitude` / `latitude` | float? | DVF | centroïde (moyenne des ventes) |

### `CityDetail` = `CityMetrics` + ces 5 blocs

| Champ | Type | Bloc |
|-------|------|------|
| `metrics_by_year` | `YearlyMetric[]` | historique annuel des prix |
| `trend` | `PriceTrendPoint[]` | tendance mensuelle |
| `demographics` | `DemographicProfile?` | profil âge/sexe |
| `transport` | `TransportProfile?` | desserte SNCF |
| `services` | `ServicesProfile?` | équipements BPE |

**`YearlyMetric`** : `year`, `prix_m2_median?`, `prix_m2_mean?`, `surface_median?`, `nb_transactions`.

**`PriceTrendPoint`** : `year`, `month` (1–12), `prix_m2_median?`, `nb_transactions`.

**`DemographicProfile`** (millésime 2022) : `year?`, `population_total?`,
`pct_moins25?`, `pct_25_64?`, `pct_65plus?`, `part_femmes?` (pourcentages).

**`TransportProfile`** :

| Champ | Type | Sens |
|-------|------|------|
| `nb_gares` | int | nb de gares dans la commune |
| `frequentation_totale` | int? | voyageurs/an cumulés |
| `frequentation_year` | int? | millésime (2024) |
| `best_segment_drg` | string? | meilleur segment SNCF (`A`/`B`/`C`) |
| `desserte_class` | string? | **classe de desserte** (enum §6) |
| `distance_gare_km` | float? | `0` si desservie, sinon distance à la gare la + proche |
| `gare_proche_uic` / `gare_proche_nom` | string? | gare la + proche (si non desservie) |

> `transport` peut être `null` (commune sans coordonnées). Si présent et
> `nb_gares = 0` → `desserte_class = "Non desservie"` + `distance_gare_km`.

**`Gare`** (endpoint `/gares`) : `code_uic`, `nom_gare`, `segment_drg?`,
`frequentation?`, `frequentation_year?`, `longitude?`, `latitude?`.

**`ServicesProfile`** (millésime 2024) :

| Champ | Type | Sens |
|-------|------|------|
| `year` | int? | millésime BPE (2024) |
| `nb_services` | int | A — services aux particuliers |
| `nb_commerces` | int | B |
| `nb_enseignement` | int | C |
| `nb_sante` | int | D — santé / social |
| `nb_transport` | int | E |
| `nb_sport_culture` | int | F |
| `nb_tourisme` | int | G |
| `nb_total` | int | total équipements |
| `nb_medecin` | int | médecins généralistes |
| `nb_pharmacie` | int | pharmacies |
| `nb_ecole` | int | écoles (mat/prim/élém) |
| `nb_supermarche` | int | supermarchés/hypermarchés |
| `nb_boulangerie` | int | boulangeries |
| `niveau_equipement` | string? | **niveau d'équipement** (enum §6) |

**`Arrondissement`** (endpoint `/arrondissements`) : mêmes champs que
`CityMetrics` mais clé `code_arrondissement` + `nom_arrondissement`, plus
`code_commune_parent`, `nom_commune_parent`.

**`HousingPriceByType`** : `code_commune`, `type_local` (`Maison`|`Appartement`),
`prix_m2_median?`, `surface_median?`, `nb_transactions`.

---

## 6. Vocabulaires (enums) — à afficher tels quels

Ces valeurs sont **stables** : on peut les mapper à des badges/couleurs/filtres.

**`type_commune`** (taille, sur la population) :
`Village` (<2k) · `Bourg` (2–5k) · `Petite ville` (5–20k) · `Ville moyenne`
(20–100k) · `Grande ville` (≥100k).

**`affordability_class`** (accessibilité, croissant = plus tendu) :
`Très abordable` · `Abordable` · `Tendu` · `Très tendu`.

**`desserte_class`** (transport) :
`Hub majeur` · `Bien desservie` · `Desservie` · `Non desservie`.

**`niveau_equipement`** (services) :
`Sous-équipée` · `Équipée` · `Bien équipée` · `Très équipée`.

**`best_segment_drg`** (SNCF) : `A` (grande gare) · `B` · `C`.

**`type_local`** (DVF) : `Maison` · `Appartement`.

**Millésimes par axe** : prix DVF `2021/2022/2024` (multi-année) · population
INSEE `2022` · revenu FiLoSoFi `2023` · transport SNCF `2024` · services BPE
`2024`. Affiche le millésime quand tu montres une valeur (transparence).

---

## 7. Recettes front

**Fiche ville** → un seul appel `GET /cities/{code}` donne tout (prix +
historique + tendance + démo + transport + services). Pour Paris/Lyon/Marseille,
ajoute `GET /cities/{code}/arrondissements` (drill-down) et `/gares` (carte).

**Liste / carte** → `GET /cities` (avec `sort`/`departement`/`q`). Chaque item
contient déjà `type_commune`, `affordability_class`, `longitude/latitude` →
suffisant pour colorer une carte sans appel supplémentaire (les blocs transport/
démo/services ne sont que dans la fiche détail).

**Recherche** → `GET /cities?q=...`. **Classement** → `sort` + `order`.

**Comparateur** → plusieurs `GET /cities/{code}` (un par commune).

---

## 8. Lineage (d'où vient chaque bloc)

```
GET /cities/{code} (CityDetail)
├─ market.city_metrics          ← DVF × INSEE × FiLoSoFi  (headline, metrics_by_year, type, accessibilité)
├─ market.city_price_trend      ← DVF                      (trend)
├─ demographics.commune_profile ← INSEE                    (demographics)
├─ mobility.commune_transport   ← SNCF                     (transport)
└─ services.commune_equipements ← INSEE BPE                (services)

/cities/{code}/arrondissements ← market.arrondissement_metrics
/cities/{code}/gares           ← mobility.gares
/housing/prices                ← market.housing_price_by_type
```

Voir aussi [`fiche_ville.md`](fiche_ville.md) et [`liste_villes.md`](liste_villes.md)
pour le détail de ces deux endpoints clés.

---

## 9. Exemple de réponse (extrait, `GET /cities/31555`)

```jsonc
{
  "code_commune": "31555", "nom_commune": "Toulouse", "year": 2024,
  "code_departement": "31", "region": "Occitanie",
  "population": 511684, "insee_ref_year": 2022, "type_commune": "Grande ville",
  "revenu_median": 24500.0, "revenu_ref_year": 2023,
  "affordability_years": 9.3, "affordability_class": "Abordable",
  "prix_m2_median": 3255.53, "nb_transactions": 13456,
  "longitude": 1.44, "latitude": 43.60,
  "metrics_by_year": [ { "year": 2021, "prix_m2_median": 3100.0 }, { "year": 2024, "prix_m2_median": 3255.5 } ],
  "trend": [ { "year": 2024, "month": 1, "prix_m2_median": 3240.0, "nb_transactions": 210 } ],
  "demographics": { "year": 2022, "pct_moins25": 35.7, "pct_25_64": 51.2, "pct_65plus": 13.1, "part_femmes": 51.4 },
  "transport": { "nb_gares": 10, "desserte_class": "Hub majeur", "distance_gare_km": 0.0, "frequentation_totale": 16101114 },
  "services": { "year": 2024, "nb_sante": 6624, "nb_medecin": 549, "nb_pharmacie": 157,
                "nb_ecole": 226, "nb_supermarche": 108, "nb_boulangerie": 298,
                "nb_total": 21503, "niveau_equipement": "Très équipée" }
}
```
