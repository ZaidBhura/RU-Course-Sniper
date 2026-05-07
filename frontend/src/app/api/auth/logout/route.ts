import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000/api";

export async function POST() {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("sniper_rt")?.value;
  const accessToken = cookieStore.get("sniper_at")?.value;

  if (refreshToken) {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {});
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.delete("sniper_at");
  res.cookies.delete("sniper_rt");
  return res;
}
