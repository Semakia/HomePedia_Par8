import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";
import { CreateUserForm } from "@/components/admin/create-user-form";
import { UsersTable } from "@/components/admin/users-table";

// Access is gated by admin/layout.tsx. Always fresh — mutations revalidate here.
export const dynamic = "force-dynamic";

export default async function AdminUsersPage() {
  const session = await auth();
  const users = await prisma.user.findMany({
    orderBy: { createdAt: "desc" },
    select: { id: true, email: true, name: true, role: true, createdAt: true },
  });

  return (
    <div className="flex flex-col gap-5">
      <CreateUserForm />
      <UsersTable rows={users} currentUserId={session?.user?.id ?? ""} />
    </div>
  );
}
