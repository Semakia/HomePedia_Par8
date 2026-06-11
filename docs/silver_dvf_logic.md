# Silver — Logique de transformation DVF

Spécification du job `src/data_processing/transformations/housing_dvf_etl.py`
(Bronze → Silver). Établie à partir du profilage du fichier brut geo-dvf
(échantillon : département 90, millésime 2024).

> Bronze = brut immuable. Tout le nettoyage/typage décrit ici se fait en Silver.

---

## 1. Structure de la source (Bronze)

- Format : CSV gzip (`.csv.gz`), encodage **UTF-8**, séparateur `,`, décimales `.`.
- **40 colonnes**, dont les utiles pour nous :

| Colonne | Usage |
|---|---|
| `id_mutation` | identifiant de la transaction (⚠️ 1 mutation = N lignes) |
| `date_mutation` | date de vente (→ `year`, `month`) |
| `nature_mutation` | type d'opération (on garde `Vente`) |
| `valeur_fonciere` | **prix total de la mutation** (répété sur chaque ligne) |
| `code_commune` | **code INSEE 5 car.** → clé de jointure INSEE |
| `nom_commune`, `code_departement`, `code_postal` | localisation |
| `type_local` | Maison / Appartement / Dépendance / Local / (NaN=terrain) |
| `surface_reelle_bati` | surface bâtie (m²) |
| `nombre_pieces_principales` | nb de pièces |
| `longitude`, `latitude` | géoloc (~99 % rempli) |

Colonnes ignorées : `lot*`, `nature_culture*`, `ancien_*`, `adresse_*`, `numero_volume`.

---

## 2. Les 3 pièges à traiter

1. **Granularité (capital)** — 1 `id_mutation` = ~3 lignes en moyenne (jusqu'à 332).
   `valeur_fonciere` est **répétée à l'identique** sur chaque ligne de la mutation.
   → Un `prix_m2` calculé ligne par ligne compte le prix total plusieurs fois. **Faux.**
2. **Lignes non résidentielles** — Dépendances, terrains (type_local NaN), locaux
   commerciaux. On ne garde que **Maison + Appartement**.
3. **Valeurs aberrantes** — `valeur_fonciere` de 1 € à 32 M€ ; `prix_m2` de 0 à
   249 000 €/m². Filtrage obligatoire.

---

## 3. Pipeline de nettoyage

```
1. nature_mutation == "Vente"
2. type_local ∈ {Maison, Appartement}
3. RÉSOLUTION GRANULARITÉ — filtre "mono-bien" :
     ne garder que les id_mutation avec EXACTEMENT 1 local habitable
     (méthode standard DVF pour un €/m² fiable ; les ventes multi-lots
      — immeubles, lots multiples — sont écartées car bruitées)
4. surface_reelle_bati > 9   ET   valeur_fonciere > 0
5. prix_m2 = valeur_fonciere / surface_reelle_bati
6. prix_m2 ∈ [500, 20 000]    (bornes anti-aberrant)
7. code_commune normalisé sur 5 caractères (lpad "0")
8. déduplication exacte
9. dérivation year / month depuis date_mutation
```

### Décision produit
Le **filtre mono-bien** (étape 3) privilégie la **fiabilité** du €/m² au prix d'un
peu de volume. Alternative non retenue pour l'instant : agréger la surface
habitable par mutation et garder le prix total (plus complet, plus bruité).

---

## 4. Schéma de sortie (Silver)

1 ligne = 1 bien résidentiel vendu.

| Colonne | Type | Note |
|---|---|---|
| `id_mutation` | string | |
| `date_mutation` | date | |
| `year` | int | partition |
| `month` | int | |
| `code_commune` | string(5) | clé INSEE |
| `code_departement` | string | partition |
| `nom_commune` | string | |
| `type_local` | string | Maison / Appartement |
| `surface_reelle_bati` | double | m² |
| `nombre_pieces_principales` | int | |
| `valeur_fonciere` | double | € |
| `prix_m2` | double | € / m² |
| `longitude`, `latitude` | double | |

- **Format** : Parquet (compression snappy)
- **Partitionnement** : `year` / `code_departement`
- **Chemin** : `s3a://<silver-bucket>/dvf/`
- **Écriture** : overwrite dynamique de partition (idempotent par année/dépt)

---

## 5. Repère de qualité (dépt 90, 2024, pipeline mono-bien)

6 679 lignes brutes → **1 213 lignes Silver** (Appartement 653 / Maison 560),
`prix_m2` médian ≈ **1 461 €/m²**, bornes `[500 ; 8 333]`, 0 null, codes commune
tous sur 5 caractères. _(Validé par dry-run pandas rejouant la logique exacte.)_


