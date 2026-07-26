import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from handlers.langfuse_tracer import LangfuseTracer

import uuid

def main():
    print("Initializing LangfuseTracer...")
    tracer = LangfuseTracer()
    print(f"Tracer active: {tracer.is_active}")

    cid = f"verify_call_{uuid.uuid4().hex[:8]}"
    trace = tracer.start_trace(
        call_id=cid,
        agent_id="agent_sales_1",
        organization_id="org_test_1",
        user_id="user_test_1",
        call_context={"direction": "inbound", "provider": "WEB_WIDGET"},
        config={"llm_model": "claude-3-5-haiku", "llm_provider": "bedrock"},
    )
    print(f"Started Trace [{cid}]: {trace}")

    with tracer.span_stt(model="deepgram") as span:
        print("Completed STT span")

    with tracer.span_tool("get_user_account", "http", arguments={"account_id": "acc_123"}) as tool_meta:
        tool_meta["result"] = {"status": "active", "balance": 100}
        print("Completed Tool span")

    gen = tracer.record_llm_generation(
        name="assistant_greeting",
        prompt="User: Hi there!",
        completion="Assistant: Hello! How can I assist you today?",
        model="claude-3-5-haiku",
    )
    print(f"Recorded LLM Generation: {gen}")

    tracer.record_score("customer_satisfaction", 5.0, comment="Successful query resolution")
    print("Recorded score")

    asyncio.run(tracer.flush_async())
    print("Flushed traces successfully!")

if __name__ == "__main__":
    main()
