import { Worker } from "bullmq";
import { redisConnection } from "../config/redis.js";
import { generateDownloadUrl } from "../config/s3.js";
import { processKbDocuments } from "../modules/kb/kb-processing-client.js";
import { assertKbProcessingSucceeded } from "../modules/kb/kb-processing-result.js";
import * as kbRepository from "../modules/kb/kb.repository.js";
import type { KbJobData, KbJobName } from "../queues/kb.queue.js";

const AI_API_URL = process.env.AI_API_URL ?? "http://localhost:5555";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";
const KB_PROCESSING_POLL_INTERVAL_MS = numberFromEnv(
  "KB_PROCESSING_POLL_INTERVAL_MS",
  2_000,
);
const KB_PROCESSING_TIMEOUT_MS = numberFromEnv(
  "KB_PROCESSING_TIMEOUT_MS",
  10 * 60 * 1_000,
);

export const kbWorker = new Worker<KbJobData, void, KbJobName>(
  "kb-ingest",
  async (job) => {
    const { kbIds, agentId, organizationId, documents } = job.data;

    // 1. Generate presigned download URLs for S3-backed documents
    const enriched = await Promise.all(
      documents.map(async (doc) => ({
        ...doc,
        presignedUrl: doc.s3Key
          ? await generateDownloadUrl(doc.s3Key)
          : undefined,
      })),
    );

    // 2. Call the apps/ai FastAPI processing endpoint and wait for async jobs.
    const body = await processKbDocuments({
      aiApiUrl: AI_API_URL,
      internalApiKey: INTERNAL_API_KEY,
      payload: { agentId, organizationId, documents: enriched },
      pollIntervalMs: KB_PROCESSING_POLL_INTERVAL_MS,
      timeoutMs: KB_PROCESSING_TIMEOUT_MS,
    });
    assertKbProcessingSucceeded(body, kbIds);

    // 3. Mark all sources as ACTIVE
    await kbRepository.markActive(kbIds, agentId);
  },
  {
    connection: redisConnection,
    concurrency: 5,
  },
);

kbWorker.on("failed", async (job, err) => {
  if (!job) return;
  console.error(`[kb-worker] job ${job.id} failed permanently`, err.message);
  const { kbIds } = job.data;
  await kbRepository
    .markError(kbIds)
    .catch((e) => console.error("[kb-worker] markError failed", e));
});

kbWorker.on("completed", (job) => {
  console.log(`[kb-worker] job ${job.id} completed`);
});

function numberFromEnv(name: string, fallback: number) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}
