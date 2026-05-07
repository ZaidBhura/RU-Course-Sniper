import { z } from "zod";

export const UserOutSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  is_superuser: z.boolean(),
  is_active: z.boolean(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export const UserPatchSchema = z.object({
  is_active: z.boolean().optional(),
  is_superuser: z.boolean().optional(),
});

export type UserOut = z.infer<typeof UserOutSchema>;
export type UserPatch = z.infer<typeof UserPatchSchema>;
