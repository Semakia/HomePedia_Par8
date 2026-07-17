"use server";

import { AuthError } from "next-auth";

import { signIn } from "@/auth";

// useActionState action: returns an error string on failure, or lets Auth.js's
// success redirect (thrown NEXT_REDIRECT) propagate.
export async function authenticate(
  _prev: string | undefined,
  formData: FormData,
): Promise<string | undefined> {
  try {
    await signIn("credentials", {
      email: formData.get("email"),
      password: formData.get("password"),
      redirectTo: "/",
    });
  } catch (error) {
    if (error instanceof AuthError) {
      return "Email ou mot de passe invalide.";
    }
    throw error; // re-throw the success redirect (and anything unexpected)
  }
}
