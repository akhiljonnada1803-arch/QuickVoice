from __future__ import annotations

import abc
import os
from typing import Any

from utils.logger import logger, redact_sensitive


def _is_truthy(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "on"}
    return bool(val)


class BaseEvaluator(abc.ABC):
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    @abc.abstractmethod
    def evaluate(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Evaluate session context and return a list of scores.
        Each score is a dict: {"name": str, "value": float | int | str, "comment": str}
        """
        pass


class LatencyEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("latency_evaluator")

    def evaluate(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        scores: list[dict[str, Any]] = []
        duration = context.get("duration_seconds")
        if duration is not None:
            scores.append({
                "name": "conversation_duration_seconds",
                "value": float(duration),
                "comment": f"Total call duration: {duration}s",
            })
        return scores


class ToolSuccessEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("tool_success_evaluator")

    def evaluate(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        scores: list[dict[str, Any]] = []
        tool_calls = context.get("tool_calls", [])
        if not tool_calls:
            return scores

        total = len(tool_calls)
        successful = sum(1 for call in tool_calls if call.get("status") == "success")
        rate = float(successful / total) if total > 0 else 1.0

        scores.append({
            "name": "tool_success_rate",
            "value": round(rate, 4),
            "comment": f"Executed {successful}/{total} tools successfully",
        })
        return scores


class RAGPerformanceEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("rag_performance_evaluator")

    def evaluate(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        scores: list[dict[str, Any]] = []
        rag_queries = context.get("rag_queries", [])
        if not rag_queries:
            return scores

        total = len(rag_queries)
        hits = sum(1 for q in rag_queries if q.get("status") == "hit" or q.get("match_count", 0) > 0)
        hit_rate = float(hits / total) if total > 0 else 0.0

        scores.append({
            "name": "rag_hit_rate",
            "value": round(hit_rate, 4),
            "comment": f"RAG hits: {hits}/{total} queries",
        })
        return scores


class BusinessMetricEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("business_metric_evaluator")

    def evaluate(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        scores: list[dict[str, Any]] = []
        transcripts = context.get("transcripts", [])
        if transcripts:
            total_words = sum(len(str(t.get("content", "")).split()) for t in transcripts)
            # Rough estimation: ~1.3 tokens per word
            est_tokens = int(total_words * 1.3)
            scores.append({
                "name": "estimated_total_tokens",
                "value": est_tokens,
                "comment": f"Estimated tokens based on {total_words} transcript words",
            })

        extracted = context.get("extracted_data", [])
        if isinstance(extracted, list):
            scores.append({
                "name": "extracted_data_fields_count",
                "value": len(extracted),
                "comment": f"Extracted {len(extracted)} structured data fields",
            })

        return scores


class EvaluationEngine:
    def __init__(self, enabled: bool | None = None):
        self._enabled = enabled if enabled is not None else _is_truthy(os.getenv("LANGFUSE_EVALS_ENABLED", "true"))
        self._evaluators: list[BaseEvaluator] = []

        # Register default evaluators
        self.register_evaluator(LatencyEvaluator())
        self.register_evaluator(ToolSuccessEvaluator())
        self.register_evaluator(RAGPerformanceEvaluator())
        self.register_evaluator(BusinessMetricEvaluator())

    def register_evaluator(self, evaluator: BaseEvaluator) -> None:
        self._evaluators.append(evaluator)

    def evaluate_and_record(self, context: dict[str, Any], tracer: Any) -> list[dict[str, Any]]:
        if not self._enabled or not tracer or not tracer.is_active:
            return []

        all_scores: list[dict[str, Any]] = []
        for evaluator in self._evaluators:
            if not evaluator.enabled:
                continue
            try:
                scores = evaluator.evaluate(context)
                for score in scores:
                    all_scores.append(score)
                    tracer.record_score(
                        name=score["name"],
                        value=score["value"],
                        comment=score.get("comment"),
                    )
            except Exception as error:
                logger.warning(
                    "[EVALUATION] Evaluator {} failed: {}",
                    evaluator.name,
                    redact_sensitive(str(error)),
                )

        return all_scores
