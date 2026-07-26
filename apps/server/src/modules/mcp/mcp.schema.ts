import { z } from "zod";

export const connectMcpSchema = z.object({
  catalogSlug: z.string().min(1).optional(),
  customUrl: z.string().url().optional(),
  displayName: z.string().min(1).max(100).optional(),
}).refine((data) => Boolean(data.catalogSlug) !== Boolean(data.customUrl), {
  message: "Provide either catalogSlug or customUrl",
});

export const attachMcpSchema = z.object({
  enabled: z.boolean().default(true),
});

export const executeMcpToolSchema = z.object({
  agentId: z.string().min(1).optional(),
  callId: z.string().min(1).optional(),
  arguments: z.record(z.string(), z.unknown()).default({}),
});

export type ConnectMcpInput = z.infer<typeof connectMcpSchema>;
export type ExecuteMcpToolInput = z.infer<typeof executeMcpToolSchema>;
