type KbProcessingItem = {
  kbId?: unknown;
  status?: unknown;
  error?: unknown;
  userMessage?: unknown;
};

type KbProcessingResponse = {
  success?: unknown;
  processed?: unknown;
  documents?: unknown;
};

function processingItemsFromResponse(body: KbProcessingResponse) {
  if (body?.success === true && Array.isArray(body.processed)) {
    return body.processed as KbProcessingItem[];
  }

  if (Array.isArray(body?.documents)) {
    return body.documents as KbProcessingItem[];
  }

  throw new Error("KB processing returned an invalid response body");
}

export function assertKbProcessingSucceeded(
  body: KbProcessingResponse,
  expectedKbIds: string[],
) {
  const processed = processingItemsFromResponse(body);
  const failures = processed.filter((item) => item.status !== "ok");
  const processedIds = new Set(
    processed
      .map((item) => (typeof item.kbId === "string" ? item.kbId : null))
      .filter((kbId): kbId is string => kbId !== null),
  );
  const missingIds = expectedKbIds.filter((kbId) => !processedIds.has(kbId));

  if (failures.length > 0 || missingIds.length > 0) {
    const failureSummary = failures
      .map((item) => {
        const kbId = typeof item.kbId === "string" ? item.kbId : "unknown";
        const error =
          typeof item.error === "string"
            ? item.error
            : typeof item.userMessage === "string"
              ? item.userMessage
              : "unknown error";
        return `${kbId}: ${error}`;
      })
      .join("; ");
    const missingSummary = missingIds.length
      ? `missing results for ${missingIds.join(", ")}`
      : "";
    const details = [failureSummary, missingSummary].filter(Boolean).join("; ");
    throw new Error(`KB processing failed: ${details}`);
  }
}
