import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { TopBar } from "@/components/layout/TopBar";
import { UserTable } from "@/components/admin/UserTable";

async function requireSuperuser() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("sniper_at")?.value;
  if (!accessToken) redirect("/dashboard");
  try {
    const payload = JSON.parse(
      Buffer.from(accessToken.split(".")[1], "base64url").toString()
    );
    if (!payload.is_superuser) redirect("/dashboard");
  } catch {
    redirect("/dashboard");
  }
}

export default async function AdminPage() {
  await requireSuperuser();

  return (
    <>
      <TopBar title="Admin" />
      <div className="p-6 max-w-4xl space-y-6">
        <div>
          <h2 className="text-xs font-mono text-muted-foreground uppercase tracking-widest mb-1">
            Users
          </h2>
          <p className="text-xs text-muted-foreground">
            Manage tenant users. You cannot modify your own roles.
          </p>
        </div>
        <UserTable />
      </div>
    </>
  );
}
