import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import prisma from "../../src/config/prisma.js";
import { BadRequestError } from "../../src/common/errors/badRequest.js";
import { createKbApiSchema } from "../../src/modules/kb/kb.schema.js";
import * as kbRepository from "../../src/modules/kb/kb.repository.js";

const originalTransaction = prisma.$transaction.bind(prisma);

afterEach(() => {
  prisma.$transaction = originalTransaction;
});

test("createKbApiSchema accepts authenticated-context payloads without caller-supplied tenant ids", () => {
  const parsed = createKbApiSchema.parse({
    agentId: "8d55565f-1111-4111-8111-f95fd03f0df2",
    userId: "attacker_user",
    organizationId: "attacker_org",
    documents: [
      {
        name: "Pricing",
        sourceType: "URL",
        url: "https://docs.quickvoice.test/pricing",
      },
    ],
  });

  assert.deepEqual(Object.keys(parsed).sort(), ["agentId", "documents"]);
});

test("createKnowledgeSources verifies the target agent belongs to the active organization before writes", async () => {
  const writes: unknown[] = [];
  prisma.$transaction = (async (callback: (tx: unknown) => Promise<unknown>) => {
    return callback({
      agent: {
        findFirst: async () => null,
      },
      knowledgeSource: {
        create: async (args: unknown) => {
          writes.push(args);
          return { kbId: "kb_1", name: "Pricing", sourceType: "URL" };
        },
      },
    });
  }) as typeof prisma.$transaction;

  await assert.rejects(
    kbRepository.createKnowledgeSources({
      organizationId: "org_123",
      userId: "user_123",
      agentId: "8d55565f-1111-4111-8111-f95fd03f0df2",
      documents: [
        {
          name: "Pricing",
          sourceType: "URL",
          url: "https://docs.quickvoice.test/pricing",
        },
      ],
    }),
    BadRequestError
  );
  assert.equal(writes.length, 0);
});
