"""Client-side OpenTelemetry tracing to the project's Application Insights.

Each conversation becomes one trace:
  invoke_workflow support-desk
    invoke_agent triage-agent
    invoke_agent policy-agent-<cond> | order-agent-<cond>
      execute_tool get_order_status / create_return   (client-executed function tools)

Foundry's server-side tracing records the same runs independently, so the
portal's Traces tab has them too. The trace id is stored with every result
row so any number in the paper can be traced back to a real run.
"""
from contextlib import contextmanager

from opentelemetry import trace

_configured = False


def setup(enable: bool = True):
    global _configured
    if _configured or not enable:
        return
    import os
    # azure-monitor-opentelemetry >= 1.8 defaults to a rate-limited sampler (5 traces/s), which silently
    # dropped client spans in the smoke run. Every conversation must be fully traced, so keep all spans.
    os.environ.setdefault("OTEL_TRACES_SAMPLER", "always_on")
    from . import foundry
    conn = foundry.app_insights_connection_string()
    if conn:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=conn)
        try:
            from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
            OpenAIInstrumentor().instrument()
        except Exception as e:  # noqa: BLE001
            print(f"[telemetry] OpenAI instrumentation not enabled: {e}")
        print("[telemetry] Exporting traces to Application Insights")
    _configured = True


tracer = trace.get_tracer("support-desk-experiment")


@contextmanager
def span(name: str, **attrs):
    with tracer.start_as_current_span(name) as s:
        for k, v in attrs.items():
            if v is not None:
                s.set_attribute(k, v if isinstance(v, (str, int, float, bool)) else str(v))
        yield s


def current_trace_id() -> str | None:
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx and ctx.trace_id else None


def flush():
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
