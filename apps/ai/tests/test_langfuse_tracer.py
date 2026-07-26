import asyncio
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from handlers.langfuse_tracer import LangfuseTracer


class LangfuseTracerTests(unittest.TestCase):
    def test_tracer_disabled_without_keys(self):
        tracer = LangfuseTracer(enabled=True, public_key="", secret_key="")
        self.assertFalse(tracer.is_active)
        self.assertIsNone(tracer.start_trace("call_123"))

        # Spans should execute cleanly as context managers
        with tracer.span_stt():
            pass

        with tracer.span_rag("search query", "agent_123") as meta:
            self.assertIsInstance(meta, dict)

        with tracer.span_tool("get_weather", "http") as tool_meta:
            self.assertIsInstance(tool_meta, dict)

        tracer.record_llm_generation("prompt", "completion")
        tracer.record_score("latency", 250)
        asyncio.run(tracer.flush_async())

    def test_tracer_mock_client(self):
        class MockLangfuse:
            def __init__(self):
                self.traces = []
                self.scores = []

            def trace(self, **kwargs):
                self.traces.append(kwargs)
                return MockTrace(self)

            def flush(self):
                pass

        class MockTrace:
            def __init__(self, parent):
                self.parent = parent
                self.spans = []
                self.generations = []

            def span(self, **kwargs):
                self.spans.append(kwargs)
                return MockSpan(self)

            def generation(self, **kwargs):
                self.generations.append(kwargs)
                return self

            def score(self, **kwargs):
                self.parent.scores.append(kwargs)

        class MockSpan:
            def __init__(self, parent):
                self.parent = parent

            def end(self, **kwargs):
                pass

        tracer = LangfuseTracer(enabled=True, public_key="pk-dummy", secret_key="sk-dummy")
        mock_client = MockLangfuse()
        tracer._client = mock_client
        tracer._is_active = True

        tracer.start_trace("call_123", agent_id="agent_abc", organization_id="org_xyz")
        self.assertEqual(len(mock_client.traces), 1)
        self.assertEqual(mock_client.traces[0]["id"], "call_123")

        with tracer.span_stt(model="deepgram"):
            pass

        with tracer.span_rag(query="company policies", agent_id="agent_abc") as rag_meta:
            rag_meta["match_count"] = 3
            rag_meta["status"] = "hit"

        with tracer.span_tool("fetch_data", "http", arguments={"id": 123}) as tool_meta:
            tool_meta["result"] = {"status": "ok"}

        tracer.record_score("tool_success_rate", 1.0)
        self.assertEqual(len(mock_client.scores), 1)
        self.assertEqual(mock_client.scores[0]["name"], "tool_success_rate")

        asyncio.run(tracer.flush_async())


if __name__ == "__main__":
    unittest.main()
