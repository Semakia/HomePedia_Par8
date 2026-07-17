"use client";

import { useActionState } from "react";

import { ROLES } from "@/lib/auth-roles";
import { createUser } from "@/app/(app)/admin/actions";
import { Card } from "@/components/ui/card";

const FIELD =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-ink outline-none transition-colors placeholder:text-muted focus:border-primary";

const ROLE_LABEL: Record<string, string> = {
  USER: "Utilisateur",
  ADMIN: "Administrateur",
};

export function CreateUserForm() {
  const [error, formAction, pending] = useActionState(createUser, undefined);

  return (
    <Card>
      <h2 className="text-sm font-semibold text-ink">Créer un compte</h2>
      <form
        action={formAction}
        className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
      >
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted">Nom</span>
          <input name="name" type="text" placeholder="Optionnel" className={FIELD} />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted">Email</span>
          <input
            name="email"
            type="email"
            required
            placeholder="vous@exemple.fr"
            className={FIELD}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted">Mot de passe</span>
          <input
            name="password"
            type="password"
            required
            minLength={8}
            placeholder="8 caractères min."
            className={FIELD}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted">Rôle</span>
          <select name="role" defaultValue="USER" className={FIELD}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r] ?? r}
              </option>
            ))}
          </select>
        </label>

        {error ? (
          <p
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 sm:col-span-2 lg:col-span-4 dark:bg-red-950/40"
          >
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-primary px-3 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60 sm:col-span-2 lg:col-span-1 lg:col-start-4"
        >
          {pending ? "Création…" : "Créer le compte"}
        </button>
      </form>
    </Card>
  );
}
