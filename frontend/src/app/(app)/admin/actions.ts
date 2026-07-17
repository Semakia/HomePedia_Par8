"use server";

import bcrypt from "bcryptjs";
import { revalidatePath } from "next/cache";

import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";
import { asRole, type Role } from "@/lib/auth-roles";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Revalidate the admin surfaces affected by an account mutation. */
function revalidateAdmin() {
  revalidatePath("/admin");
  revalidatePath("/admin/utilisateurs");
}

/**
 * Guard: every admin mutation re-checks the caller's role server-side. The proxy
 * already gates /admin, but server actions must never trust the client — an
 * action is a public POST endpoint. Returns the current admin's user id.
 */
async function requireAdmin(): Promise<string> {
  const session = await auth();
  if (asRole(session?.user?.role) !== "ADMIN" || !session?.user?.id) {
    throw new Error("Accès refusé.");
  }
  return session.user.id;
}

/** Whether there is still another ADMIN besides `exceptId`. */
async function hasOtherAdmin(exceptId: string): Promise<boolean> {
  const count = await prisma.user.count({
    where: { role: "ADMIN", id: { not: exceptId } },
  });
  return count > 0;
}

/**
 * Promote/demote a user. Refuses self-modification (an admin can't change their
 * own role from this screen) and refuses demoting the last remaining admin.
 * Returns an error string on refusal, or undefined on success.
 */
export async function setUserRole(
  userId: string,
  role: Role,
): Promise<string | undefined> {
  const adminId = await requireAdmin();
  const nextRole = asRole(role);

  if (userId === adminId) {
    return "Vous ne pouvez pas modifier votre propre rôle.";
  }

  const target = await prisma.user.findUnique({
    where: { id: userId },
    select: { role: true },
  });
  if (!target) return "Compte introuvable.";

  if (asRole(target.role) === "ADMIN" && nextRole !== "ADMIN") {
    if (!(await hasOtherAdmin(userId))) {
      return "Impossible de rétrograder le dernier administrateur.";
    }
  }

  await prisma.user.update({ where: { id: userId }, data: { role: nextRole } });
  revalidateAdmin();
}

/**
 * Delete a user. Refuses deleting yourself and refuses deleting the last admin.
 * Returns an error string on refusal, or undefined on success.
 */
export async function deleteUser(userId: string): Promise<string | undefined> {
  const adminId = await requireAdmin();

  if (userId === adminId) {
    return "Vous ne pouvez pas supprimer votre propre compte.";
  }

  const target = await prisma.user.findUnique({
    where: { id: userId },
    select: { role: true },
  });
  if (!target) return "Compte introuvable.";

  if (asRole(target.role) === "ADMIN" && !(await hasOtherAdmin(userId))) {
    return "Impossible de supprimer le dernier administrateur.";
  }

  await prisma.user.delete({ where: { id: userId } });
  revalidateAdmin();
}

/**
 * useActionState action: create an account with an explicit role (unlike the
 * public register flow, which is always USER and auto-signs-in). Returns an
 * error string on failure, or undefined on success.
 */
export async function createUser(
  _prev: string | undefined,
  formData: FormData,
): Promise<string | undefined> {
  await requireAdmin();

  const name = String(formData.get("name") ?? "").trim();
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const password = String(formData.get("password") ?? "");
  const role = asRole(formData.get("role"));

  if (!EMAIL_RE.test(email)) return "Adresse email invalide.";
  if (password.length < 8) {
    return "Le mot de passe doit contenir au moins 8 caractères.";
  }

  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) return "Un compte existe déjà avec cet email.";

  const passwordHash = await bcrypt.hash(password, 10);
  try {
    await prisma.user.create({
      data: { email, name: name || null, passwordHash, role },
    });
  } catch {
    // Unique-constraint race between the check above and the insert.
    return "Un compte existe déjà avec cet email.";
  }

  revalidateAdmin();
}
