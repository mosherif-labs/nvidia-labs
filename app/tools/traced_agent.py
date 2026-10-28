import os
import sys

from openinference.instrumentation import using_attributes
from openinference.instrumentation.openai import OpenAIInstrumentor
from phoenix.otel import register

tp = register(
    project_name="aai-agent",
    endpoint=os.environ.get("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
)
OpenAIInstrumentor().instrument(tracer_provider=tp)  # every LLM call becomes a span
tracer = tp.get_tracer(__name__)

from app.tools import agent  # import AFTER instrumenting the client
from app.tools.registry import registry


def traced_call(name: str, raw: str) -> str:  # every tool call becomes a span too
    with tracer.start_as_current_span(f"tool.{name}") as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        span.set_attribute("tool.name", name)
        span.set_attribute("input.value", raw)
        try:
            out = registry.call(name, raw)
        except Exception as e:
            span.set_attribute("error.type", type(e).__name__)
            raise
        span.set_attribute("output.value", out[:1000])
        return out


if __name__ == "__main__":
    case_id, question = sys.argv[1], " ".join(sys.argv[2:])
    with (
        using_attributes(
            session_id=case_id,
            metadata={"case_id": case_id, "model": agent.MODEL},
            tags=["aai", "day15"],
        ),
        tracer.start_as_current_span(f"case {case_id}") as root,
    ):
        root.set_attribute("openinference.span.kind", "AGENT")
        r = agent.run(question, call=traced_call)
        root.set_attribute("output.value", str(r["answer"]))
    print(r)
