"use server";

import bcrypt from "bcryptjs";
import { AuthError } from "next-auth";

import { signIn } from "@/auth";
import { prisma } from "@/lib/prisma";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// useActionState action: creates the account then signs the user in. Returns an
// error string on validation/duplicate failure; the success sign-in redirect
// (thrown NEXT_REDIRECT) propagates.
export async function registerUser(
  _prev: string | undefined,
  formData: FormData,
): Promise<string | undefined> {
  const name = String(formData.get("name") ?? "").trim();
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const password = String(formData.get("password") ?? "");

  if (!EMAIL_RE.test(email)) return "Adresse email invalide.";
  if (password.length < 8) {
    return "Le mot de passe doit contenir au moins 8 caractères.";
  }

  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) return "Un compte existe déjà avec cet email.";

  const passwordHash = await bcrypt.hash(password, 10);
  try {
    await prisma.user.create({
      data: { email, name: name || null, passwordHash },
    });
  } catch {
    // Unique-constraint race between the check above and the insert.
    return "Un compte existe déjà avec cet email.";
  }

  try {
    await signIn("credentials", { email, password, redirectTo: "/" });
  } catch (error) {
    if (error instanceof AuthError) {
      // Account created but auto-login failed — send them to the login screen.
      return "Compte créé. Veuillez vous connecter.";
    }
    throw error; // success redirect
  }
}
