import { apiClient } from "./client";
import { UserOut, UserOutSchema, UserPatch } from "@/lib/schemas/user";
import {
  WatchedIndexOut,
  WatchedIndexOutSchema,
} from "@/lib/schemas/watchlist";
import { NotificationLogOut, NotificationLogOutSchema } from "@/lib/schemas/logs";
import { z } from "zod";

export async function adminGetUsers(): Promise<UserOut[]> {
  const { data } = await apiClient.get("/admin/users");
  return z.array(UserOutSchema).parse(data);
}

export async function adminPatchUser(
  id: string,
  body: UserPatch
): Promise<UserOut> {
  const { data } = await apiClient.patch(`/admin/users/${id}`, body);
  return UserOutSchema.parse(data);
}

export async function adminGetWatchlists(): Promise<WatchedIndexOut[]> {
  const { data } = await apiClient.get("/admin/watchlists");
  return z.array(WatchedIndexOutSchema).parse(data);
}

export async function adminGetLogs(): Promise<NotificationLogOut[]> {
  const { data } = await apiClient.get("/admin/logs");
  return z.array(NotificationLogOutSchema).parse(data);
}
