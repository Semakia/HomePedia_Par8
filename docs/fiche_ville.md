# La fiche ville HOMEPEDIA (`GET /api/v1/cities/{code_commune}`)

La fiche ville est la **vue 360° d'une commune** servie par l'API. Elle agrège,
en une seule réponse, les 4 axes de décision immobilière croisés par HOMEPEDIA :

| Axe | Question | Source | Millésime |
|-----|----------|--------|-----------|
| 💶 **Prix** | Combien coûte le m² (et son évolution) ? | DVF (Etalab) | 2021 / 2022 / 2024 |
| 🏘️ **Typologie** | Village ou grande ville ? | dérivé population INSEE | 2022 |
| 👥 **Démographie** | Quel profil d'âge / sexe ? | INSEE (recensement) | 2022 |
| 🧮 **Accessibilité financière** | Logement abordable vs revenus ? | DVF × FiLoSoFi | prix / revenu 2023 |
| 🚆 **Desserte transport** | Bien relié au train ? | SNCF (open data) | 2024 |

Chaque axe est **pré-calculé dans le Gold** (pattern data marts) et simplement
lu par l'API. Les millésimes sont **exposés explicitement** (transparence) car
ils diffèrent par source.

---

## 1. Le « headline » (millésime le plus récent)

La racine de la réponse = les métriques de la commune sur l'**année la plus
récente disponible** (DVF). Champs clés :

```
code_commune, nom_commune, code_departement, region, year
population, insee_ref_year                 # INSEE
type_commune                               # Village / Bourg / Petite ville / Ville moyenne / Grande ville
revenu_median, revenu_ref_year             # FiLoSoFi (niveau de vie médian €/an)
affordability_years, m2_par_an, affordability_class
prix_m2_median, prix_m2_mean, surface_median, nb_transactions
longitude, latitude
```

- **Typologie** (`type_commune`) : 5 paliers sur la population — Village `<2k`,
  Bourg `2–5k`, Petite ville `5–20k`, Ville moyenne `20–100k`, Grande ville `≥100k`.
- **Accessibilité financière** (indice relatif, pas un taux bancaire) :
  - `affordability_years` = `prix_m2 × 70 / revenu_median` (années de revenu
    pour un logement de 70 m²) ;
  - `m2_par_an` = `revenu_median / prix_m2` (m² pour un an de revenu) ;
  - `affordability_class` : Très abordable `<7` / Abordable `7–12` / Tendu
    `12–18` / Très tendu `≥18` ans.

## 2. `metrics_by_year` — l'historique annuel

Une ligne par millésime DVF (prix médian/moyen, surface médiane, nb de
transactions). Permet d'afficher l'évolution du prix sans mélanger les années
(chaque année garde sa propre médiane).

## 3. `trend` — la tendance mensuelle

Une ligne par (année, mois) : prix m² médian + nb de transactions. Granularité
fine pour la courbe de la fiche.

## 4. `demographics` — le profil âge/sexe

Objet (millésime 2022), **pourcentages** prêts pour la segmentation :

```
population_total, pct_moins25, pct_25_64, pct_65plus, part_femmes
```

Tranches d'âge disjointes agrégées en 3 classes (moins de 25 / 25–64 / 65+).
*(Ex. Toulouse = ville jeune : ~36 % de moins de 25 ans.)*

## 5. `transport` — la desserte ferroviaire (SNCF)

```
nb_gares, frequentation_totale, frequentation_year, best_segment_drg
desserte_class            # Hub majeur / Bien desservie / Desservie / Non desservie
distance_gare_km          # 0 si desservie ; sinon distance (haversine) à la gare la plus proche
gare_proche_uic, gare_proche_nom   # gare la plus proche (communes non desservies)
```

- `desserte_class` dérive du **segment SNCF** (A = Hub majeur, B = Bien
  desservie, C = Desservie) ; commune sans gare → **Non desservie** avec la
  distance à la gare la plus proche (calcul haversine, sans service externe).
- Distance plafonnée à 150 km (au-delà = pas d'accès ferroviaire pertinent,
  ex. DOM sans train → champ nul).

---

## Endpoints liés

| Endpoint | Retour |
|----------|--------|
| `GET /api/v1/cities` | liste paginée/triable/filtrable (headline année récente par commune) |
| `GET /api/v1/cities/{code}` | **la fiche ville complète** (ci-dessus) |
| `GET /api/v1/cities/{code}/arrondissements` | détail par arrondissement (Paris/Lyon/Marseille) — `[]` sinon |
| `GET /api/v1/cities/{code}/gares` | gares de la commune (triées par fréquentation) |

> **Paris / Lyon / Marseille** : DVF et SNCF codent ces villes par
> *arrondissement*. La fiche ville **roule** les arrondissements vers la commune
> mère (75056 / 69123 / 13055) ; le détail par arrondissement est exposé via
> `/arrondissements`.

---

## D'où vient chaque bloc (lineage Gold)

```
fiche ville (GET /cities/{code})
├─ market.city_metrics          ← DVF × INSEE × FiLoSoFi   (prix, pop, type, revenu, accessibilité, headline + metrics_by_year)
├─ market.city_price_trend      ← DVF                       (trend mensuel)
├─ demographics.commune_profile ← INSEE (recensement)       (demographics)
└─ mobility.commune_transport   ← SNCF                      (transport + distance gare)

GET /cities/{code}/arrondissements ← market.arrondissement_metrics
GET /cities/{code}/gares           ← mobility.gares
```

Toutes les tables Gold sont reconstruites par les ETL Spark (`silver_to_gold`,
`mobility_gold`) et alimentées en JDBC dans le Postgres servi. Les contrôles
qualité (`config/data_quality/gold_*.yaml`) et le catalogue OpenMetadata portent
sur ces mêmes tables.

---

## Exemple (extrait, Paris `75056`)

```json
{
  "code_commune": "75056", "nom_commune": "Paris", "year": 2024,
  "region": "Île-de-France", "type_commune": "Grande ville",
  "population": 2113705, "insee_ref_year": 2022,
  "revenu_median": 33650.0, "revenu_ref_year": 2023,
  "prix_m2_median": 9562.5, "affordability_class": "Très tendu",
  "demographics": { "pct_moins25": 26.9, "pct_25_64": 55.6, "pct_65plus": 17.5, "part_femmes": 53.0 },
  "transport": { "nb_gares": 28, "desserte_class": "Hub majeur", "distance_gare_km": 0.0 },
  "metrics_by_year": [ { "year": 2021, "prix_m2_median": 10833.3 }, { "year": 2024, "prix_m2_median": 9562.5 } ],
  "trend": [ ... ]
}
```
