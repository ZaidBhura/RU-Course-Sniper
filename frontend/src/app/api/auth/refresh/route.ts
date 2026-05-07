import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000/api";
const IS_PROD = process.env.NODE_ENV === "production";
const ACCESS_TOKEN_MAX_AGE = 30 * 60;
const REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60;

export async function POST() {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("sniper_rt")?.value;

  if (!refreshToken) {
    return NextResponse.json({ detail: "No refresh token" }, { status: 401 });
  }

  const upstream = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  const data = await upstream.json();

  if (!upstream.ok) {
    const res = NextResponse.json(data, { status: upstream.status });
    res.cookies.delete("sniper_at");
    res.cookies.delete("sniper_rt");
    return res;
  }

  const { access_token, refresh_token, token_type } = data;

  const res = NextResponse.json({ access_token, token_type });

  res.cookies.set("sniper_at", access_token, {
    httpOnly: false,
    secure: IS_PROD,
    sameSite: "strict",
    maxAge: ACCESS_TOKEN_MAX_AGE,
    path: "/",
  });

  res.cookies.set("sniper_rt", refresh_token, {
    httpOnly: true,
    secure: IS_PROD,
    sameSite: "strict",
    maxAge: REFRESH_TOKEN_MAX_AGE,
    path: "/",
  });

  return res;
}
