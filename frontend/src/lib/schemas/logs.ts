import { z } from "zod";

export const NotificationLogOutSchema = z.object({
  id: z.string().uuid(),
  index_number: z.number().int(),
  semester_code: z.string(),
  channel_type: z.string(),
  event_type: z.enum(["open_notify", "close_reset"]),
  delivery_status: z.enum(["sent", "failed", "skipped"]),
  course_subject: z.string().nullable(),
  course_number: z.string().nullable(),
  course_title: z.string().nullable(),
  webreg_url: z.string().nullable(),
  created_at: z.string().datetime(),
});

export type NotificationLogOut = z.infer<typeof NotificationLogOutSchema>;
