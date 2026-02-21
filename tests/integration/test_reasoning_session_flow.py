from fastapi.testclient import TestClient


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


def test_reasoning_run_completed_flow(client: TestClient, headers: dict):
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


def test_reasoning_clarification_flow(client: TestClient, headers: dict):
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
