from src.app.services.observability import langfuse_sink as sink_module
from src.app.services.observability.runtime_config import replace_langfuse_runtime_config


class _FakeLangfuse:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.traces = []
        self.events = []
        self.flush_count = 0

    def trace(self, **kwargs):
        self.traces.append(kwargs)
        return {"id": kwargs.get("id")}

    def event(self, **kwargs):
        self.events.append(kwargs)

    def flush(self):
        self.flush_count += 1


def test_langfuse_sink_emits_trace_and_event(monkeypatch):
    replace_langfuse_runtime_config(
        {
            "enabled": True,
            "public_key": "pk-test",
            "secret_key": "sk-test",
            "host": "http://localhost:3000",
            "environment": "test",
            "release": "v-test",
            "audit_payload_max_chars": 24000,
        }
    )
    monkeypatch.setattr(sink_module, "Langfuse", _FakeLangfuse)
    monkeypatch.setattr(sink_module, "_LANGFUSE_IMPORT_ERROR", None)
    sink_module.LangfuseSink._instance = None

    sink = sink_module.LangfuseSink()
    sink.emit_event(
        tenant_id="tenant-a",
        session_id="session-1",
        trace_id="trace-1",
        step="planning",
        event_type="task_planned",
        payload={"foo": "bar"},
    )

    assert sink._disabled is False
    assert sink._client is not None
    assert len(sink._client.traces) == 1
    assert sink._client.traces[0]["id"] == "trace-1"
    assert len(sink._client.events) == 1
    assert sink._client.events[0]["trace_id"] == "trace-1"
    assert sink._client.flush_count == 1
