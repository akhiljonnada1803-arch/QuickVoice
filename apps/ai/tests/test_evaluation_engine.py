import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from handlers.evaluation_engine import (
    BaseEvaluator,
    BusinessMetricEvaluator,
    EvaluationEngine,
    LatencyEvaluator,
    RAGPerformanceEvaluator,
    ToolSuccessEvaluator,
)


class MockTracer:
    def __init__(self):
        self.is_active = True
        self.scores = []

    def record_score(self, name, value, comment=None):
        self.scores.append({"name": name, "value": value, "comment": comment})


class CustomSafetyEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("safety_evaluator")

    def evaluate(self, context: dict) -> list[dict]:
        return [{
            "name": "safety_score",
            "value": 1.0,
            "comment": "No policy violations detected",
        }]


class EvaluationEngineTests(unittest.TestCase):
    def test_default_evaluators_calculation(self):
        engine = EvaluationEngine(enabled=True)
        tracer = MockTracer()

        context = {
            "duration_seconds": 45,
            "transcripts": [
                {"role": "user", "content": "Hello how are you"},
                {"role": "agent", "content": "I am doing well, thank you!"},
            ],
            "extracted_data": [{"name": "intent", "value": "support"}],
            "tool_calls": [
                {"tool_name": "check_status", "status": "success"},
                {"tool_name": "update_ticket", "status": "success"},
            ],
            "rag_queries": [
                {"query": "pricing", "status": "hit", "match_count": 2},
            ],
        }

        scores = engine.evaluate_and_record(context, tracer)
        self.assertTrue(len(scores) >= 4)
        score_names = [s["name"] for s in scores]

        self.assertIn("conversation_duration_seconds", score_names)
        self.assertIn("tool_success_rate", score_names)
        self.assertIn("rag_hit_rate", score_names)
        self.assertIn("estimated_total_tokens", score_names)

        # Check tool success rate value
        tool_score = next(s for s in scores if s["name"] == "tool_success_rate")
        self.assertEqual(tool_score["value"], 1.0)

        # Check tracer received records
        self.assertEqual(len(tracer.scores), len(scores))

    def test_custom_evaluator_registration(self):
        engine = EvaluationEngine(enabled=True)
        engine.register_evaluator(CustomSafetyEvaluator())
        tracer = MockTracer()

        context = {"duration_seconds": 10}
        scores = engine.evaluate_and_record(context, tracer)

        score_names = [s["name"] for s in scores]
        self.assertIn("safety_score", score_names)

    def test_disabled_engine_returns_empty(self):
        engine = EvaluationEngine(enabled=False)
        tracer = MockTracer()
        context = {"duration_seconds": 10}
        scores = engine.evaluate_and_record(context, tracer)
        self.assertEqual(scores, [])


if __name__ == "__main__":
    unittest.main()
