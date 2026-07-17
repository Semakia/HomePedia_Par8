# HOMEPEDIA — Frontend (Next.js)

App Next.js 16 (App Router). Elle consomme l'**API Gold** (lecture seule) pour
les données immobilières et gère ses **propres comptes** (auth front-owned :
Auth.js v5 + Prisma/SQLite).

> ⚠️ Next.js 16 a des changements cassants (le middleware s'appelle désormais
> `proxy.ts`, Prisma 7 configure la connexion hors du schéma, etc.). Voir
> `AGENTS.md`.

## Prérequis

- **Node ≥ 22** (le seed utilise `node --experimental-strip-types`).
- Outils de build C/C++ (`better-sqlite3` est un module natif compilé à l'install).

## Installation

```bash
cd frontend
npm install            # installe les deps ; `postinstall` lance `prisma generate`
```

## Configuration (obligatoire pour que la connexion fonctionne)

La base SQLite (`prisma/dev.db`) et les fichiers `.env*` **ne sont pas versionnés** :
chaque dev crée les siens à partir de `.env.example`.

1. **`frontend/.env`** (secrets serveur) :
   ```
   DATABASE_URL="file:./prisma/dev.db"
   AUTH_SECRET="<valeur générée>"
   ```
   ⚠️ `AUTH_SECRET` **doit** être défini, sinon la signature des sessions JWT
   échoue et l'authentification ne marche pas. Générez la vôtre (locale, pas
   besoin qu'elle soit identique entre devs) :
   ```bash
   npx auth secret        # ou : openssl rand -base64 33
   ```

2. **`frontend/.env.local`** (URL de l'API Gold, injectée au build) :
   ```
   NEXT_PUBLIC_API_URL="http://127.0.0.1:8001"
   ```
   > Préférez `127.0.0.1` à `localhost` : si Node résout `localhost` en IPv6 en
   > premier, le fetch côté serveur échoue avec `ECONNREFUSED`.

## Base de données (comptes)

```bash
npm run db:migrate     # applique la migration → crée prisma/dev.db
npm run db:seed        # crée les comptes de démo :
                       #   admin@homepedia.fr / admin1234   (ADMIN)
                       #   user@homepedia.fr  / user1234    (USER)
```

> L'inscription via `/register` crée uniquement un compte **USER**. Pour un
> **ADMIN**, utilisez le seed, ou promouvez un compte depuis `/admin`
> (nécessite d'être déjà connecté en admin).

Utilitaire : `npm run db:studio` ouvre Prisma Studio pour inspecter la base.

## Lancer

```bash
npm run dev
```

Ouvrez http://localhost:3000 (ou le port indiqué si 3000 est déjà pris).

## Accès & rôles

- L'app est **accessible sans être connecté** — carte, statistiques, tableau,
  analyse sont publics.
- La connexion débloque l'espace **`/admin`** (réservé aux comptes **ADMIN**) et
  l'affichage du compte dans la barre latérale.
- Un anonyme qui visite `/admin` est redirigé vers `/login` (puis renvoyé sur
  `/admin` après connexion) ; un non-admin est renvoyé à l'accueil.

## Scripts

| Commande | Rôle |
|---|---|
| `npm run dev` | Serveur de dev |
| `npm run build` / `npm run start` | Build de prod / démarrage |
| `npm run lint` | ESLint |
| `npm run db:migrate` | Crée/applique les migrations Prisma |
| `npm run db:seed` | Insère les comptes de démo |
| `npm run db:studio` | Prisma Studio |

## En cas de problème

- **La connexion échoue / erreur de session** → `AUTH_SECRET` absent ou vide
  dans `.env`.
- **`Table \"User\" does not exist`** → lancez `npm run db:migrate`.
- **Aucune donnée / badge « Données mockées »** → l'API Gold n'est pas joignable
  sur `NEXT_PUBLIC_API_URL` ; l'app bascule alors sur des données de démo.
