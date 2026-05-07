import { z } from "zod";

export const WatchedIndexCreateSchema = z.object({
  index_number: z
    .number({ required_error: "Index number is required" })
    .int()
    .min(1, "Index must be at least 1")
    .max(99999, "Index must be at most 99999"),
  label: z
    .string()
    .max(200, "Label must be at most 200 characters")
    .optional()
    .or(z.literal("")),
  semester_code: z
    .string()
    .regex(/^\d{5}$/, "Semester code must be 5 digits")
    .default("12026"),
});

export const WatchedIndexPatchSchema = z.object({
  label: z
    .string()
    .max(200, "Label must be at most 200 characters")
    .optional()
    .nullable(),
  is_active: z.boolean().optional(),
});

export const WatchedIndexOutSchema = z.object({
  id: z.string().uuid(),
  index_number: z.number().int(),
  label: z.string().nullable(),
  semester_code: z.string(),
  is_active: z.boolean(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export type WatchedIndexCreate = z.infer<typeof WatchedIndexCreateSchema>;
export type WatchedIndexPatch = z.infer<typeof WatchedIndexPatchSchema>;
export type WatchedIndexOut = z.infer<typeof WatchedIndexOutSchema>;
