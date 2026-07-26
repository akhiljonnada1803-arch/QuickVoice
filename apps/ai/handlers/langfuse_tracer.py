from __future__ import annotations

import asyncio
import contextlib
import os
import time
from typing import Any

from pathlib import Path
from dotenv import load_dotenv

from utils.logger import logger, redact_sensitive
from utils.metrics import emit_metric

_BASE_DIR = Path(__file__).resolve().parent.parent
for _env_name in (".env.local", ".env.dev", ".env"):
    _env_file = _BASE_DIR / _env_name
    if _env_file.exists():
        load_dotenv(_env_file)

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None


def _is_truthy(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "on"}
    return bool(val)


class LangfuseTracer:
    """Production-grade telemetry tracer for QuickVoice voice AI pipeline using Langfuse.

    Provides root trace initialization, child span context managers for STT, RAG, and HTTP tool calls,
    LLM generation recording with usage/PII redaction, scoring, and non-blocking asynchronous flushing.
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        enabled: bool | None = None,
        max_retries: int | None = None,
    ):
        """Initialize the LangfuseTracer client using explicit arguments or environment variables."""
        self._enabled = enabled if enabled is not None else _is_truthy(os.getenv("LANGFUSE_ENABLED", "true"))
        self._public_key = public_key if public_key is not None else os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self._secret_key = secret_key if secret_key is not None else os.getenv("LANGFUSE_SECRET_KEY", "")
        self._host = host if host is not None else os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        self._max_retries = max_retries if max_retries is not None else int(os.getenv("LANGFUSE_MAX_RETRIES", "3"))

        self._client: Any = None
        self._trace: Any = None
        self._is_active = False

        if self._enabled and Langfuse is not None and self._public_key and self._secret_key:
            try:
                try:
                    self._client = Langfuse(
                        public_key=self._public_key,
                        secret_key=self._secret_key,
                        host=self._host,
                        max_retries=self._max_retries,
                    )
                except TypeError:
                    self._client = Langfuse(
                        public_key=self._public_key,
                        secret_key=self._secret_key,
                        host=self._host,
                    )
                self._is_active = True
                logger.info("[LANGFUSE] Client initialized successfully for host={}", self._host)
            except Exception as error:
                logger.warning("[LANGFUSE] Initialization failed: {}", redact_sensitive(str(error)))
                self._is_active = False
        else:
            if self._enabled and not (self._public_key and self._secret_key):
                logger.info("[LANGFUSE] Disabled: missing public or secret key")
            self._is_active = False

    @property
    def is_active(self) -> bool:
        """Return True if Langfuse client is enabled and successfully authenticated."""
        return self._is_active

    def start_trace(
        self,
        call_id: str,
        agent_id: str | None = None,
        organization_id: str | None = None,
        user_id: str | None = None,
        call_context: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> Any:
        """Start a top-level root trace observation for an inbound/outbound voice call."""
        if not self._is_active or not self._client:
            return None

        ctx = call_context or {}
        cfg = config or {}
        zero_pii = bool(cfg.get("zero_pii_retention"))

        metadata = {
            "call_id": call_id,
            "agent_id": agent_id or ctx.get("agent_id") or cfg.get("agent_id") or "",
            "organization_id": organization_id or cfg.get("organization_id") or "",
            "user_id": user_id or cfg.get("user_id") or "",
            "direction": ctx.get("direction", "inbound"),
            "provider": ctx.get("provider") or cfg.get("provider") or "WEB_WIDGET",
            "model": cfg.get("llm_model", ""),
            "model_provider": cfg.get("llm_provider", ""),
            "stt_provider": cfg.get("stt_model", ""),
            "tts_provider": cfg.get("tts_model", ""),
            "voice_model": cfg.get("voice", ""),
            "deployment_environment": os.getenv("NODE_ENV", os.getenv("ENVIRONMENT", "development")),
            "application_version": os.getenv("APP_VERSION", "0.1.0"),
            "zero_pii_retention": zero_pii,
        }

        try:
            if hasattr(self._client, "trace"):
                self._trace = self._client.trace(
                    id=call_id,
                    name="voice_call",
                    user_id=metadata["user_id"] if not zero_pii else "redacted",
                    metadata=metadata,
                    tags=[metadata["provider"], metadata["deployment_environment"]],
                )
            elif hasattr(self._client, "start_observation"):
                self._trace = self._client.start_observation(
                    name="voice_call",
                    as_type="span",
                    metadata=metadata,
                )
            else:
                self._trace = None
            emit_metric("langfuse_trace_started", call_id=call_id)
            return self._trace
        except Exception as error:
            logger.warning("[LANGFUSE] Trace creation failed for call {}: {}", call_id, redact_sensitive(str(error)))
            return None

    @contextlib.contextmanager
    def span_stt(self, model: str | None = None):
        """Context manager to measure and record STT audio recognition latency and model details."""
        start_time = time.perf_counter()
        span: Any = None
        if self._is_active and self._trace:
            try:
                if hasattr(self._trace, "span"):
                    span = self._trace.span(name="stt_recognition", metadata={"model": model or ""})
                elif hasattr(self._client, "start_observation"):
                    span = self._client.start_observation(
                        name="stt_recognition",
                        as_type="span",
                        metadata={"model": model or ""},
                    )
            except Exception:
                span = None
        try:
            yield span
        finally:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            if span:
                try:
                    if hasattr(span, "update"):
                        span.update(metadata={"latency_ms": elapsed_ms})
                    if hasattr(span, "end"):
                        span.end()
                except Exception:
                    pass

    @contextlib.contextmanager
    def span_rag(self, query: str, agent_id: str, top_k: int = 5, zero_pii: bool = False):
        """Context manager to trace RAG Knowledge Base retrieval queries, match counts, and search latency."""
        start_time = time.perf_counter()
        span: Any = None
        sanitized_query = "redacted" if zero_pii else query
        if self._is_active and self._trace:
            try:
                if hasattr(self._trace, "span"):
                    span = self._trace.span(
                        name="rag_retrieval",
                        input={"query": sanitized_query, "agent_id": agent_id, "top_k": top_k},
                    )
                elif hasattr(self._client, "start_observation"):
                    span = self._client.start_observation(
                        name="rag_retrieval",
                        as_type="span",
                        input={"query": sanitized_query, "agent_id": agent_id, "top_k": top_k},
                    )
            except Exception:
                span = None
        rag_meta: dict[str, Any] = {"status": "pending"}
        try:
            yield rag_meta
        except Exception as exc:
            rag_meta["status"] = "error"
            rag_meta["error"] = str(exc)
            raise
        finally:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            rag_meta["total_latency_ms"] = elapsed_ms
            if span:
                try:
                    out = {
                        "status": rag_meta.get("status", "hit"),
                        "match_count": rag_meta.get("match_count", 0),
                        "embedding_latency_ms": rag_meta.get("embedding_latency_ms", 0),
                        "search_latency_ms": rag_meta.get("search_latency_ms", 0),
                    }
                    if hasattr(span, "update"):
                        span.update(output=out, metadata=rag_meta)
                    if hasattr(span, "end"):
                        span.end()
                except Exception:
                    pass

    @contextlib.contextmanager
    def span_tool(
        self,
        tool_name: str,
        tool_type: str = "http",
        arguments: dict[str, Any] | None = None,
        zero_pii: bool = False,
    ):
        """Context manager to trace external HTTP or MCP tool executions, inputs, outputs, and status."""
        start_time = time.perf_counter()
        span: Any = None
        sanitized_args = {} if zero_pii else redact_sensitive(arguments or {})
        if self._is_active and self._trace:
            try:
                if hasattr(self._trace, "span"):
                    span = self._trace.span(
                        name=f"tool:{tool_name}",
                        input={"tool_name": tool_name, "tool_type": tool_type, "arguments": sanitized_args},
                    )
                elif hasattr(self._client, "start_observation"):
                    span = self._client.start_observation(
                        name=f"tool:{tool_name}",
                        as_type="span",
                        input={"tool_name": tool_name, "tool_type": tool_type, "arguments": sanitized_args},
                    )
            except Exception:
                span = None
        tool_meta: dict[str, Any] = {"status": "success", "retry_count": 0}
        try:
            yield tool_meta
        except Exception as exc:
            tool_meta["status"] = "error"
            tool_meta["exception"] = str(exc)
            raise
        finally:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            tool_meta["execution_time_ms"] = elapsed_ms
            if span:
                try:
                    output = tool_meta.get("result")
                    sanitized_output = "redacted" if zero_pii else redact_sensitive(output or {})
                    out = {"status": tool_meta.get("status"), "result": sanitized_output}
                    meta = {
                        "execution_time_ms": elapsed_ms,
                        "retry_count": tool_meta.get("retry_count", 0),
                        "response_size_bytes": tool_meta.get("response_size_bytes", 0),
                    }
                    if hasattr(span, "update"):
                        span.update(output=out, metadata=meta)
                    if hasattr(span, "end"):
                        span.end()
                except Exception:
                    pass

    def record_llm_generation(
        self,
        name: str = "llm_turn",
        prompt: Any = None,
        completion: Any = None,
        model: str | None = None,
        usage: dict[str, int] | None = None,
        zero_pii: bool = False,
    ) -> Any:
        """Record an LLM generation step with model details, prompt input, completion output, and token usage."""
        if not self._is_active or not self._trace:
            return None

        try:
            sanitized_prompt = "redacted" if zero_pii else redact_sensitive(prompt)
            sanitized_completion = "redacted" if zero_pii else redact_sensitive(completion)
            if hasattr(self._trace, "generation"):
                return self._trace.generation(
                    name=name,
                    model=model or "",
                    input=sanitized_prompt,
                    output=sanitized_completion,
                    usage=usage or {},
                )
            elif hasattr(self._client, "start_observation"):
                gen = self._client.start_observation(
                    name=name,
                    as_type="generation",
                    model=model or "",
                    input=sanitized_prompt,
                    output=sanitized_completion,
                )
                if hasattr(gen, "end"):
                    gen.end()
                return gen
        except Exception as error:
            logger.warning("[LANGFUSE] Record generation failed: {}", redact_sensitive(str(error)))
            return None

    def record_score(self, name: str, value: float | int | str, comment: str | None = None) -> None:
        """Record an evaluation or user feedback score attached to the active trace observation."""
        if not self._is_active or not self._trace:
            return

        try:
            if hasattr(self._trace, "score"):
                self._trace.score(name=name, value=value, comment=comment or "")
            elif hasattr(self._client, "create_score"):
                trace_id = getattr(self._trace, "trace_id", getattr(self._trace, "id", None))
                self._client.create_score(name=name, value=value, comment=comment or "", trace_id=trace_id)
            elif hasattr(self._client, "score"):
                self._client.score(name=name, value=value, comment=comment or "")
        except Exception as error:
            logger.warning("[LANGFUSE] Record score failed: {}", redact_sensitive(str(error)))

    async def flush_async(self) -> None:
        """Asynchronously flush buffered telemetry batches without blocking the main event loop."""
        if not self._is_active or not self._client:
            return

        try:
            await asyncio.to_thread(self._client.flush)
            emit_metric("langfuse_flushed")
            logger.info("[LANGFUSE] Successfully flushed traces")
        except Exception as error:
            logger.warning("[LANGFUSE] Flush failed: {}", redact_sensitive(str(error)))
            emit_metric("langfuse_flush_error")
