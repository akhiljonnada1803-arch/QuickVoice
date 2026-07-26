import { apiClient } from "@/src/lib/api/client";
import type {
  ApiEnvelope,
  KbSourceType,
  KnowledgeSource,
} from "@/src/lib/api/types";

export interface KbDocumentInput {
  name: string;
  sourceType: KbSourceType;
  url?: string;
  s3Key?: string;
  originalFileName?: string;
}

export interface CreateKbInput {
  organizationId: string;
  userId: string;
  agentId?: string | null;
  documents: KbDocumentInput[];
}

export interface UploadUrlResponse {
  uploadUrl: string;
  s3Key: string;
}

export const kbApi = {
  list: async (agentId?: string): Promise<KnowledgeSource[]> => {
    const res = await apiClient.get<ApiEnvelope<KnowledgeSource[]>>("/kb", {
      params: agentId ? { agentId } : undefined,
    });
    return res.data.data;
  },
  create: async (input: CreateKbInput): Promise<KnowledgeSource[]> => {
    const res = await apiClient.post<ApiEnvelope<KnowledgeSource[]>>("/kb", input);
    return res.data.data;
  },
  remove: async (kbId: string): Promise<void> => {
    await apiClient.delete(`/kb/${kbId}`);
  },
  getUploadUrl: async (fileName: string, contentType: string): Promise<UploadUrlResponse> => {
    const res = await apiClient.get<ApiEnvelope<UploadUrlResponse>>("/kb/upload-url", {
      params: { fileName, contentType },
    });
    return res.data.data;
  },
};
