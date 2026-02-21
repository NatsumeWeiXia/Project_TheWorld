import pytest
from fastapi.testclient import TestClient

from src.app.services.llm.langchain_client import LangChainLLMClient


def _create_class(client: TestClient, headers: dict, code: str, name: str) -> int:
    resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": code, "name": name, "description": ""},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    return body["data"]["id"]


def _create_attribute(client: TestClient, headers: dict, code: str, name: str) -> int:
    resp = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": code, "name": name, "data_type": "string", "required": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    return body["data"]["attribute_id"]


def _bind_attribute(client: TestClient, headers: dict, class_id: int, attr_id: int) -> None:
    resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_id]},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def _create_capability(client: TestClient, headers: dict, class_id: int, code: str, name: str) -> int:
    resp = client.post(
        "/api/v1/ontology/capabilities",
        headers=headers,
        json={
            "code": code,
            "name": name,
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "domain_groups": [[class_id]],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    return body["data"]["capability_id"]


def _create_relation(
    client: TestClient,
    headers: dict,
    code: str,
    name: str,
    domain_class_ids: list[int],
    range_class_ids: list[int],
) -> int:
    resp = client.post(
        "/api/v1/ontology/object-properties",
        headers=headers,
        json={
            "code": code,
            "name": name,
            "description": "",
            "domain_class_ids": domain_class_ids,
            "range_class_ids": range_class_ids,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    return body["data"]["object_property_id"]


def _upsert_tenant_llm_config(client: TestClient, headers: dict) -> None:
    resp = client.put(
        "/api/v1/config/tenant-llm",
        headers=headers,
        json={
            "provider": "deepseek",
            "model": "deepseek-reasoner",
            "api_key": "tenant-a-secret-key",
            "base_url": "http://127.0.0.1:1/v1",
            "timeout_ms": 1000,
            "enable_thinking": True,
            "fallback_provider": "qwen",
            "fallback_model": "qwen3.5-plus",
            "extra_json": {},
            "status": 1,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


@pytest.fixture
def mock_reasoning_llm(monkeypatch):
    def _mock_invoke_json(runtime_cfg: dict, system_prompt: str, user_payload: dict, schema_hint: dict | None = None, audit_callback=None):
        if callable(audit_callback):
            audit_callback("llm_prompt_sent", {"messages": [{"role": "system", "content": system_prompt}]})

        if "query" in user_payload and "intent" not in user_payload and "candidates" not in user_payload:
            result = {
                "keywords": ["手机号"],
                "business_elements": [{"name": "手机号", "value": "15101330234", "role": "filter"}],
                "goal_actions": ["查询"],
                "intent_summary": str(user_payload.get("query") or ""),
            }
        elif "candidates" in user_payload:
            codes = [str((item or {}).get("code") or "").strip() for item in (user_payload.get("candidates") or [])]
            codes = [code for code in codes if code]
            result = {
                "input_ontology_codes": ([codes[0]] if codes else []),
                "target_ontology_codes": [],
                "reason": "mock anchor",
            }
        elif "capabilities" in user_payload and "object_properties" in user_payload:
            capabilities = user_payload.get("capabilities") or []
            object_properties = user_payload.get("object_properties") or []
            if capabilities:
                result = {
                    "action": "execute_capability",
                    "capability_code": capabilities[0].get("code"),
                    "object_property_code": "",
                    "reason": "mock choose capability",
                }
            else:
                result = {
                    "action": "execute_object_property",
                    "capability_code": "",
                    "object_property_code": (object_properties[0] or {}).get("code"),
                    "reason": "mock choose object property",
                }
        elif "capability_detail" in user_payload:
            catalog = user_payload.get("attribute_catalog") or []
            field_name = (catalog[0] or {}).get("field_name") if catalog else None
            result = {
                "mode": "query",
                "class_id": user_payload.get("ontology", {}).get("class_id"),
                "filters": ([{"field": field_name, "op": "eq", "value": "15101330234"}] if field_name else []),
                "group_by": [],
                "metrics": [{"agg": "count", "alias": "count"}],
                "page": 1,
                "page_size": 20,
                "sort_field": None,
                "sort_order": "asc",
                "reason": "mock capability execute",
            }
        elif "object_property_detail" in user_payload:
            target_options = user_payload.get("target_ontology_options") or []
            target_code = target_options[0] if target_options else ""
            catalogs = user_payload.get("target_attribute_catalogs") or {}
            target_catalog = catalogs.get(target_code) or []
            field_name = (target_catalog[0] or {}).get("field_name") if target_catalog else None
            result = {
                "target_ontology_code": target_code,
                "mode": "query",
                "filters": ([{"field": field_name, "op": "eq", "value": "15101330234"}] if field_name else []),
                "group_by": [],
                "metrics": [{"agg": "count", "alias": "count"}],
                "page": 1,
                "page_size": 20,
                "sort_field": None,
                "sort_order": "asc",
                "reason": "mock object property execute",
            }
        else:
            result = schema_hint or {}

        if callable(audit_callback):
            audit_callback("llm_response_received", {"content": result})
        return result

    monkeypatch.setattr(LangChainLLMClient, "invoke_json", staticmethod(_mock_invoke_json))
    monkeypatch.setattr(
        LangChainLLMClient,
        "summarize_with_context",
        staticmethod(lambda runtime_cfg, query, ontology, selected_task, audit_callback=None: "mock summary"),
    )


def test_reasoning_run_completed_flow(client: TestClient, headers: dict, mock_reasoning_llm):
    _upsert_tenant_llm_config(client, headers)
    class_id = _create_class(client, headers, "user_profile", "用户画像")
    attr_id = _create_attribute(client, headers, "mobile", "手机号")
    _bind_attribute(client, headers, class_id, attr_id)
    _create_capability(client, headers, class_id, "query_user", "查询用户")
    table_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:create-table",
        headers=headers,
    )
    assert table_resp.status_code == 200
    assert table_resp.json()["code"] == 0

    create_resp = client.post(
        "/api/v1/reasoning/sessions",
        headers=headers,
        json={"user_input": "请根据手机号查询用户信息", "metadata": {}},
    )
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 0
    session_id = create_body["data"]["session_id"]

    run_resp = client.post(
        f"/api/v1/reasoning/sessions/{session_id}/run",
        headers=headers,
        json={},
    )
    assert run_resp.status_code == 200
    run_body = run_resp.json()
    assert run_body["code"] == 0
    assert run_body["data"]["status"] == "completed"
    assert run_body["data"]["tasks"]

    trace_resp = client.get(f"/api/v1/reasoning/sessions/{session_id}/trace", headers=headers)
    assert trace_resp.status_code == 200
    trace_body = trace_resp.json()
    assert trace_body["code"] == 0
    event_types = [item["event_type"] for item in trace_body["data"]["items"]]
    assert "intent_parsed" in event_types
    assert "attributes_matched" in event_types
    assert "ontologies_located" in event_types
    assert "task_planned" in event_types
    assert "session_completed" in event_types


def test_reasoning_clarification_flow(client: TestClient, headers: dict, mock_reasoning_llm):
    _upsert_tenant_llm_config(client, headers)
    create_resp = client.post(
        "/api/v1/reasoning/sessions",
        headers=headers,
        json={"user_input": "帮我处理一下", "metadata": {}},
    )
    session_id = create_resp.json()["data"]["session_id"]

    run_resp = client.post(
        f"/api/v1/reasoning/sessions/{session_id}/run",
        headers=headers,
        json={},
    )
    assert run_resp.status_code == 200
    body = run_resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "waiting_clarification"
    clarification_id = body["data"]["clarification"]["clarification_id"]
    assert clarification_id

    clarify_resp = client.post(
        f"/api/v1/reasoning/sessions/{session_id}/clarify",
        headers=headers,
        json={"answer": {"keyword": "手机号"}},
    )
    assert clarify_resp.status_code == 200
    clarify_body = clarify_resp.json()
    assert clarify_body["code"] == 0
    assert clarify_body["data"]["status"] == "created"


def test_reasoning_object_property_execute_flow(client: TestClient, headers: dict, mock_reasoning_llm):
    _upsert_tenant_llm_config(client, headers)
    entry_class_id = _create_class(client, headers, "entry_entity", "入口实体")
    target_class_id = _create_class(client, headers, "target_entity", "目标实体")
    attr_id = _create_attribute(client, headers, "entry_key", "入口键")
    _bind_attribute(client, headers, entry_class_id, attr_id)
    _create_relation(
        client,
        headers,
        "entry_to_target",
        "入口到目标",
        [entry_class_id],
        [target_class_id],
    )
    target_attr_id = _create_attribute(client, headers, "target_name", "目标名称")
    _bind_attribute(client, headers, target_class_id, target_attr_id)
    table_resp = client.post(
        f"/api/v1/ontology/classes/{target_class_id}/table-binding:create-table",
        headers=headers,
    )
    assert table_resp.status_code == 200
    assert table_resp.json()["code"] == 0

    create_resp = client.post(
        "/api/v1/reasoning/sessions",
        headers=headers,
        json={"user_input": "请处理入口键相关任务", "metadata": {}},
    )
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 0
    session_id = create_body["data"]["session_id"]

    run_resp = client.post(
        f"/api/v1/reasoning/sessions/{session_id}/run",
        headers=headers,
        json={},
    )
    assert run_resp.status_code == 200
    run_body = run_resp.json()
    assert run_body["code"] == 0
    assert run_body["data"]["status"] == "completed"
    assert run_body["data"]["tasks"]
    assert run_body["data"]["tasks"][0]["task_type"] == "object_property"
    assert run_body["data"]["result"]["data_execution_mode"] == "query"
    assert run_body["data"]["result"]["data_execution"] is not None

    trace_resp = client.get(
        f"/api/v1/reasoning/sessions/{session_id}/trace",
        headers=headers,
    )
    assert trace_resp.status_code == 200
    trace_items = trace_resp.json()["data"]["items"]
    event_types = [item["event_type"] for item in trace_items]
    assert "mcp_call_requested" in event_types
    assert "mcp_call_completed" in event_types


def test_reasoning_run_fails_when_llm_unavailable(client: TestClient, headers: dict):
    _upsert_tenant_llm_config(client, headers)
    class_id = _create_class(client, headers, "unavailable_case", "不可用测试")
    attr_id = _create_attribute(client, headers, "mobile_fail", "手机号")
    _bind_attribute(client, headers, class_id, attr_id)
    _create_capability(client, headers, class_id, "query_user_fail", "查询用户")
    table_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:create-table",
        headers=headers,
    )
    assert table_resp.status_code == 200
    assert table_resp.json()["code"] == 0

    create_resp = client.post(
        "/api/v1/reasoning/sessions",
        headers=headers,
        json={"user_input": "请根据手机号查询用户信息", "metadata": {}},
    )
    session_id = create_resp.json()["data"]["session_id"]

    run_resp = client.post(
        f"/api/v1/reasoning/sessions/{session_id}/run",
        headers=headers,
        json={},
    )
    assert run_resp.status_code == 400
    body = run_resp.json()
    assert body["code"] == 9000
    assert "llm decision failed" in body["message"]
