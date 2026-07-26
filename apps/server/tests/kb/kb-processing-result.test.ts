import assert from "node:assert/strict";
import { test } from "node:test";

import { assertKbProcessingSucceeded } from "../../src/modules/kb/kb-processing-result.js";

test("assertKbProcessingSucceeded accepts successful per-document results", () => {
  assert.doesNotThrow(() =>
    assertKbProcessingSucceeded(
      {
        success: true,
        processed: [
          { kbId: "kb_1", status: "ok" },
          { kbId: "kb_2", status: "ok" },
        ],
      },
      ["kb_1", "kb_2"],
    ),
  );
});

test("assertKbProcessingSucceeded accepts successful async job document results", () => {
  assert.doesNotThrow(() =>
    assertKbProcessingSucceeded(
      {
        jobId: "kbjob_123",
        status: "succeeded",
        documents: [
          { kbId: "kb_1", status: "ok" },
          { kbId: "kb_2", status: "ok" },
        ],
      },
      ["kb_1", "kb_2"],
    ),
  );
});

test("assertKbProcessingSucceeded rejects per-document failures in a 200 response", () => {
  assert.throws(
    () =>
      assertKbProcessingSucceeded(
        {
          success: true,
          processed: [
            { kbId: "kb_1", status: "ok" },
            {
              kbId: "kb_2",
              status: "error",
              error: "PINECONE_API_KEY missing",
            },
          ],
        },
        ["kb_1", "kb_2"],
      ),
    /KB processing failed: kb_2: PINECONE_API_KEY missing/,
  );
});

test("assertKbProcessingSucceeded rejects missing document results", () => {
  assert.throws(
    () =>
      assertKbProcessingSucceeded(
        {
          success: true,
          processed: [{ kbId: "kb_1", status: "ok" }],
        },
        ["kb_1", "kb_2"],
      ),
    /missing results for kb_2/,
  );
});
