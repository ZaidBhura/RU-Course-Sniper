import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000/api";

export async function GET() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("sniper_at")?.value;

  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const upstream = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
