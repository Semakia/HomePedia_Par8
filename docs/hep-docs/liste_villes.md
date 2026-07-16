# La liste des villes HOMEPEDIA (`GET /api/v1/cities`)

Endpoint de **recherche / parcours** des communes : retourne une page de
communes, chacune sur son **millésime le plus récent** (le « headline »). C'est
ce qui alimente la carte, les classements et la recherche du front.

> Le détail complet d'une commune (démographie, transport, historique, tendance)
> est servi par la **fiche ville** `GET /cities/{code}` — voir
> [fiche_ville.md](fiche_ville.md). La liste ne renvoie que le headline.

---

## Paramètres de requête

| Param | Type | Défaut | Rôle |
|-------|------|--------|------|
| `departement` | str | – | Filtre exact sur le code département (`75`, `2A`, `971`…) |
| `q` | str | – | Recherche par nom, **insensible à la casse** (`LIKE %q%`) |
| `sort` | str | `prix_m2_median` | Colonne de tri (liste blanche, voir ci-dessous) |
| `order` | `asc`\|`desc` | `desc` | Sens du tri |
| `page` | int ≥ 1 | `1` | Numéro de page |
| `size` | int 1–200 | `50` | Taille de page |

**Colonnes de tri autorisées** (liste blanche → tri injection-safe) :
`prix_m2_median`, `nb_transactions`, `population`, `nom_commune`.
Toute autre valeur retombe sur `prix_m2_median`.

---

## Comportement

1. **Headline par commune** : pour chaque commune, on garde **l'année DVF la
   plus récente** (`DISTINCT ON (code_commune) … ORDER BY year DESC`) — une seule
   ligne par ville, jamais de doublon multi-année.
2. **Tri** sur le set ainsi obtenu, avec **`NULLS LAST`** : les communes sans la
   métrique triée (ex. pas de revenu) passent en fin, jamais en tête.
3. **Pagination** classique (`page` / `size`).
4. Paris/Lyon/Marseille apparaissent **une seule fois** (arrondissements roulés
   vers la commune mère).

---

## Réponse — enveloppe paginée

```json
{
  "items": [ /* CityMetrics, voir ci-dessous */ ],
  "total": 32448,   // nb total de communes correspondant au filtre
  "page": 1,
  "size": 50,
  "pages": 649      // ceil(total / size)
}
```

Chaque `item` est un **`CityMetrics`** (le headline, sans les blocs détail) :

```
code_commune, year, nom_commune, code_departement, region
population, insee_ref_year, type_commune
revenu_median, revenu_ref_year, affordability_years, m2_par_an, affordability_class
prix_m2_median, prix_m2_mean, surface_median, nb_transactions
longitude, latitude
```

> Les champs `type_commune` et `affordability_class` sont déjà présents dans
> chaque item → le front peut **segmenter / colorer** la liste ou la carte sans
> appel supplémentaire.

---

## Exemples

```http
GET /api/v1/cities?sort=population&order=desc&size=3
```
→ les 3 plus grandes villes (Paris, Marseille, Lyon).

```http
GET /api/v1/cities?departement=69&sort=prix_m2_median&order=asc
```
→ communes du Rhône, des moins chères aux plus chères.

```http
GET /api/v1/cities?q=bourg&page=1&size=20
```
→ communes dont le nom contient « bourg ».

---

## Source

Tout vient de **`market.city_metrics`** (DVF × INSEE × FiLoSoFi), via le
repository Postgres. Pas de jointure démographie/transport ici : la liste reste
légère et rapide (lecture indexée + pagination).

## Extensions possibles (non implémentées)

- Filtres serveur supplémentaires : `type_commune`, `affordability_class`,
  `desserte_class` (nécessiterait de joindre `mobility.commune_transport`).
- Tri par `revenu_median` ou `affordability_years` (ajouter à la liste blanche
  `_CITY_SORTS`).
- Recherche géographique (rayon autour d'un point) via les `longitude/latitude`.
