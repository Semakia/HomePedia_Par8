"use server";

import { signOut } from "@/auth";

// Server Action used by the sidebar logout form. Clears the session cookie and
// sends the user back to the login screen.
export async function logout() {
  await signOut({ redirectTo: "/login" });
}
