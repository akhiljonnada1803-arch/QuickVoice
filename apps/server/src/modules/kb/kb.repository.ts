import { kbStatus } from "../../../prisma/generated/prisma/client.js";
import { BadRequestError } from "../../common/errors/badRequest.js";
import prisma from "../../config/prisma.js";
import type { CreateKbArgs, ListKbArgs } from "./kb.schema.js";

// Create one KnowledgeSource row per document in a single transaction.
// All start as PROCESSING — Agent.knowledgeSourcesCount is NOT updated here;
// it should be incremented when the ingestion callback flips status to ACTIVE.
export const createKnowledgeSources = async (input: CreateKbArgs) => {
  return prisma.$transaction(async (tx) => {
    const agent = await tx.agent.findFirst({
      where: { agentId: input.agentId, organizationId: input.organizationId },
      select: { agentId: true },
    });
    if (!agent) {
      throw new BadRequestError("Agent not found in active organization");
    }

    const rows = await Promise.all(
      input.documents.map((doc) =>
        tx.knowledgeSource.create({
          data: {
            organizationId: input.organizationId,
            agentId: input.agentId,
            userId: input.userId,
            name: doc.name,
            originalFileName: doc.originalFileName ?? null,
            storagePath:
              doc.sourceType === "URL"
                ? (doc.url as string)
                : (doc.s3Key as string),
            sourceType: doc.sourceType,
            status: kbStatus.PROCESSING,
          },
        })
      )
    );

    const docs = rows.map((row, i) => ({
      id: row.kbId,
      name: row.name,
      type: row.sourceType.toLowerCase(),
      url: input.documents[i]!.url ?? null,
      s3Key: input.documents[i]!.s3Key ?? null,
    }));

    return { rows, docs };
  });
};

export const listByOrg = async (args: ListKbArgs) => {
  const { organizationId, agentId } = args;
  return prisma.knowledgeSource.findMany({
    where: {
      organizationId,
      ...(agentId && { agentId }),
    },
    orderBy: { uploadedAt: "desc" },
  });
};

export const getByIdForOrg = async (kbId: string, organizationId: string) => {
  return prisma.knowledgeSource.findFirst({
    where: { kbId, organizationId },
  });
};

// Mark KB sources as ACTIVE, set lastIndexedAt, and increment the agent's
// knowledgeSourcesCount — all atomically.
export const markActive = async (kbIds: string[], agentId: string) => {
  return prisma.$transaction(async (tx) => {
    await tx.knowledgeSource.updateMany({
      where: { kbId: { in: kbIds } },
      data: { status: kbStatus.ACTIVE, lastIndexedAt: new Date() },
    });

    await tx.agent.update({
      where: { agentId },
      data: { knowledgeSourcesCount: { increment: kbIds.length } },
    });
  });
};

// Mark KB sources as ERROR after ingestion failure.
export const markError = async (kbIds: string[]) => {
  await prisma.knowledgeSource.updateMany({
    where: { kbId: { in: kbIds } },
    data: { status: kbStatus.ERROR },
  });
};

// Hard delete. If the source was ACTIVE, also decrements Agent.knowledgeSourcesCount.
// External asset cleanup is handled by kb.service.ts before this DB delete.
export const deleteKnowledgeSource = async (
  kbId: string,
  organizationId: string
) => {
  return prisma.$transaction(async (tx) => {
    // Tenant-safe fetch — ensures the row belongs to this org.
    const row = await tx.knowledgeSource.findFirst({
      where: { kbId, organizationId },
    });
    if (!row) return null;

    await tx.knowledgeSource.delete({ where: { kbId } });

    // Decrement the agent counter only if the source was ACTIVE.
    if (row.status === kbStatus.ACTIVE && row.agentId) {
      await tx.agent.update({
        where: { agentId: row.agentId },
        data: { knowledgeSourcesCount: { decrement: 1 } },
      });
    }

    return row;
  });
};
