import {z} from "zod"
import { sourceType } from "../../../prisma/generated/prisma/client.js";

export const kbItemApiSchema =  z
  .object({
    name: z.string().min(1, "Document name is required"),
    sourceType: z.nativeEnum(sourceType),
    url: z
      .union([
        z.string().url("Invalid URL"),
        z.literal(""),
        z.null(),
        z.undefined(),
      ])
      .optional()
      .nullable(),
    s3Key: z.string().optional().nullable(),
    originalFileName: z.string().optional().nullable(),
  })
  .superRefine((data, ctx) => {
    if (data.sourceType === sourceType.URL) {
      if (!data.url || data.url === "") {
        ctx.addIssue({
          path: ["url"],
          message: "URL is required for URL source",
          code: z.ZodIssueCode.custom,
        });
      }
    } else {
      if (!data.s3Key) {
        ctx.addIssue({
          path: ["s3Key"],
          message: "File is required for this source type",
          code: z.ZodIssueCode.custom,
        });
      }
    }
  });
  export const createKbApiSchema = z
  .object({
    agentId: z.string().min(1, "No agent selected").uuid("Invalid agentId"),
    documents: z.array(kbItemApiSchema).min(1, "At least one document is required"),
  }).strip()

export type CreateKbInput = z.infer<typeof createKbApiSchema>;
export type CreateKbArgs = CreateKbInput & {
  organizationId: string;
  userId: string;
};

export const listKbQuerySchema = z.object({
  agentId: z.string().uuid().optional(),
});
export type ListKbQuery = z.infer<typeof listKbQuerySchema>;
export type ListKbArgs = ListKbQuery & { organizationId: string };
