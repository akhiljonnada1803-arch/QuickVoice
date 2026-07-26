import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from handlers.calllog_handler import build_call_log_payload, post_call_log_with_retry
from utils.logger import logger, redact_sensitive


class CallFinalizer:
    def __init__(
        self,
        *,
        config: dict[str, Any],
        call_context: dict[str, Any],
        started_at: datetime,
        recording_path: str | None,
        transcript_reader: Callable[[], list[dict[str, Any]]],
        post_call_log: Callable[[dict[str, Any]], Awaitable[Any]] | None = None,
        tracer: Any = None,
        evaluation_engine: Any = None,
        tool_calls: list[dict[str, Any]] | None = None,
        rag_queries: list[dict[str, Any]] | None = None,
    ):
        self._config = config
        self._call_context = call_context
        self._started_at = started_at
        self._recording_path = recording_path
        self._transcript_reader = transcript_reader
        self._post_call_log = post_call_log or post_call_log_with_retry
        self._tracer = tracer
        self._evaluation_engine = evaluation_engine
        self._tool_calls = tool_calls or []
        self._rag_queries = rag_queries or []
        self._lock = asyncio.Lock()
        self._completed = False

    async def finalize(self) -> None:
        async with self._lock:
            if self._completed:
                return
            self._completed = True

            ended_at = datetime.now(timezone.utc)
            zero_pii_retention = bool(self._config.get("zero_pii_retention"))
            transcript = [] if zero_pii_retention else self._transcript_reader()
            payload = build_call_log_payload(
                config=self._config,
                call_context=self._call_context,
                started_at=self._started_at,
                ended_at=ended_at,
                recording_path=None if zero_pii_retention else self._recording_path,
                transcripts=transcript,
            )
            if zero_pii_retention:
                payload["metadata"]["zeroPiiRetention"] = True
                payload["extractedData"] = []
                payload["evaluatedData"] = []
            if self._config.get("retention_days") is not None:
                payload["metadata"]["retentionDays"] = self._config.get("retention_days")

            if self._evaluation_engine and self._tracer and getattr(self._tracer, "is_active", False):
                eval_context = {
                    "duration_seconds": payload.get("durationSeconds", 0),
                    "transcripts": transcript,
                    "extracted_data": payload.get("extractedData", []),
                    "tool_calls": self._tool_calls,
                    "rag_queries": self._rag_queries,
                }
                try:
                    self._evaluation_engine.evaluate_and_record(eval_context, self._tracer)
                except Exception as eval_err:
                    logger.warning("[EVALUATION] Failed running evaluations: {}", redact_sensitive(str(eval_err)))

            await self._post_call_log(payload)
            logger.info("[CALL_LOG] finalized call {}", redact_sensitive({"callId": payload["callId"]}))

            if self._tracer and getattr(self._tracer, "is_active", False):
                try:
                    await self._tracer.flush_async()
                except Exception as flush_err:
                    logger.warning("[LANGFUSE] Finalizer flush failed: {}", redact_sensitive(str(flush_err)))
