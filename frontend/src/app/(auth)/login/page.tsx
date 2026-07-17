"use client";

import Link from "next/link";
import { useActionState } from "react";

import { authenticate } from "./actions";

const FIELD =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-ink outline-none transition-colors placeholder:text-muted focus:border-primary";

export default function LoginPage() {
  const [error, formAction, pending] = useActionState(authenticate, undefined);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold text-ink">Connexion</h1>
        <p className="mt-1 text-sm text-muted">
          Accédez à votre espace HOMEPEDIA.
        </p>
      </div>

      <form action={formAction} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink">Email</span>
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="vous@exemple.fr"
            className={FIELD}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink">Mot de passe</span>
          <input
            name="password"
            type="password"
            required
            autoComplete="current-password"
            placeholder="••••••••"
            className={FIELD}
          />
        </label>

        {error ? (
          <p
            role="alert"
            className="rounded-lg bg-primary-soft px-3 py-2 text-sm text-primary"
          >
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={pending}
          className="mt-1 rounded-lg bg-primary px-3 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {pending ? "Connexion…" : "Se connecter"}
        </button>
      </form>

      <p className="text-center text-sm text-muted">
        Pas encore de compte ?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Créer un compte
        </Link>
      </p>
    </div>
  );
}
