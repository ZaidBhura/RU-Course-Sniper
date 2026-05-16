import { z } from "zod";

export const WatchedIndexCreateSchema = z.object({
  index_number: z.preprocess(
    (val) => (val === "" || val === undefined || val === null ? undefined : Number(val)),
    z
      .number({ required_error: "Index number is required" })
      .int("Must be a whole number")
      .min(1, "Index must be at least 1")
      .max(99999, "Index must be at most 99999")
  ),
  label: z
    .string()
    .max(200, "Label must be at most 200 characters")
    .optional()
    .or(z.literal("")),
  semester_code: z
    .string()
    .regex(/^\d{5}$/, "Semester code must be 5 digits")
    .default("92026"),
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
  course_name: z.string().nullable(),
  semester_code: z.string(),
  is_active: z.boolean(),
  status: z.enum(["watching", "opened"]),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export type WatchedIndexCreate = z.infer<typeof WatchedIndexCreateSchema>;
export type WatchedIndexPatch = z.infer<typeof WatchedIndexPatchSchema>;
export type WatchedIndexOut = z.infer<typeof WatchedIndexOutSchema>;
