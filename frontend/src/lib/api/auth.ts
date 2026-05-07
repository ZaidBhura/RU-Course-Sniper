import { LoginInput, RegisterInput } from "@/lib/schemas/auth";
import { UserOut, UserOutSchema } from "@/lib/schemas/user";

async function bffPost(path: string, body?: unknown): Promise<Response> {
  return fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
}

export async function login(data: LoginInput): Promise<void> {
  const res = await bffPost("/api/auth/login", data);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Invalid email or password");
  }
}

export async function register(data: RegisterInput): Promise<void> {
  const res = await bffPost("/api/auth/register", data);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Registration failed");
  }
}

export async function logout(refreshToken: string): Promise<void> {
  await bffPost("/api/auth/logout", { refresh_token: refreshToken });
}

export async function getMe(): Promise<UserOut> {
  const res = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (!res.ok) throw new Error("Not authenticated");
  return UserOutSchema.parse(await res.json());
}
