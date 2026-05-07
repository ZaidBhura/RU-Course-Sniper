import { apiClient } from "./client";
import { NotificationLogOut, NotificationLogOutSchema } from "@/lib/schemas/logs";
import { z } from "zod";

export async function getLogs(): Promise<NotificationLogOut[]> {
  const { data } = await apiClient.get("/logs/");
  return z.array(NotificationLogOutSchema).parse(data);
}
