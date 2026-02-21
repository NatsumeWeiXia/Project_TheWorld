from fastapi.testclient import TestClient


def _create_class(client: TestClient, headers: dict, code: str, name: str) -> int:
    resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": code, "name": name, "description": ""},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _create_attribute(client: TestClient, headers: dict, code: str, name: str) -> int:
    resp = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": code, "name": name, "data_type": "string", "required": False},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["attribute_id"]


def _bind_attribute(client: TestClient, headers: dict, class_id: int, attr_id: int) -> None:
    resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_id]},
    )
    assert resp.status_code == 200


def _create_capability(client: TestClient, headers: dict, class_id: int, code: str, name: str) -> None:
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


def test_tenant_llm_config_upsert_and_get_masked(client: TestClient, headers: dict):
    upsert_resp = client.put(
        "/api/v1/config/tenant-llm",
        headers=headers,
        json={
            "provider": "deepseek",
            "model": "deepseek-reasoner",
            "api_key": "tenant-a-secret-key",
            "base_url": "",
            "timeout_ms": 25000,
            "enable_thinking": True,
            "fallback_provider": "qwen",
            "fallback_model": "qwen3.5-plus",
            "extra_json": {"temperature": 0.1},
            "status": 1,
        },
    )
    assert upsert_resp.status_code == 200
    assert upsert_resp.json()["code"] == 0

    get_resp = client.get("/api/v1/config/tenant-llm", headers=headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["code"] == 0
    assert body["data"]["provider"] == "deepseek"
    assert body["data"]["model"] == "deepseek-reasoner"
    assert body["data"]["api_key_masked"]
    assert "tenant-a-secret-key" not in str(body)


def test_tenant_llm_verify_returns_structured_result(client: TestClient, headers: dict):
    client.put(
        "/api/v1/config/tenant-llm",
        headers=headers,
        json={
            "provider": "qwen",
            "model": "qwen3.5-plus",
            "api_key": "tenant-a-secret-key",
            "base_url": "https://example.invalid/v1",
            "timeout_ms": 1500,
            "enable_thinking": True,
            "fallback_provider": None,
            "fallback_model": None,
            "extra_json": {},
            "status": 1,
        },
    )

    verify_resp = client.post(
        "/api/v1/config/tenant-llm:verify",
        headers=headers,
        json={},
    )
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["code"] == 0
    assert body["data"]["provider"] == "openai-compatible" or body["data"]["provider"] == "qwen"
    assert isinstance(body["data"]["ok"], bool)


def test_reasoning_uses_tenant_llm_route_metadata(client: TestClient, headers: dict):
    client.put(
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

    class_id = _create_class(client, headers, "order", "订单")
    attr_id = _create_attribute(client, headers, "order_no", "订单号")
    _bind_attribute(client, headers, class_id, attr_id)
    _create_capability(client, headers, class_id, "query_order", "查询订单")
    table_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:create-table",
        headers=headers,
    )
    assert table_resp.status_code == 200
    assert table_resp.json()["code"] == 0

    create_resp = client.post(
        "/api/v1/reasoning/sessions",
        headers=headers,
        json={"user_input": "帮我查询订单号对应的订单", "metadata": {}},
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
    assert body["data"]["status"] == "completed"
    llm_route = body["data"]["result"]["llm_route"]
    assert llm_route["provider"] == "deepseek"
    assert llm_route["model"] == "deepseek-reasoner"
    assert llm_route["has_fallback"] is True


def test_tenant_llm_config_api_key_isolated_by_provider(client: TestClient, headers: dict):
    first_resp = client.put(
        "/api/v1/config/tenant-llm",
        headers=headers,
        json={
            "provider": "deepseek",
            "model": "deepseek-reasoner",
            "api_key": "deepseek-key-001",
            "base_url": "https://api.deepseek.com",
            "timeout_ms": 30000,
            "enable_thinking": False,
            "fallback_provider": None,
            "fallback_model": None,
            "extra_json": {},
            "status": 1,
        },
    )
    assert first_resp.status_code == 200
    assert first_resp.json()["code"] == 0

    second_resp = client.put(
        "/api/v1/config/tenant-llm",
        headers=headers,
        json={
            "provider": "qwen",
            "model": "qwen3.5-plus",
            "api_key": "qwen-key-002",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "timeout_ms": 30000,
            "enable_thinking": True,
            "fallback_provider": "deepseek",
            "fallback_model": "deepseek-reasoner",
            "extra_json": {},
            "status": 1,
        },
    )
    assert second_resp.status_code == 200
    assert second_resp.json()["code"] == 0

    get_resp = client.get("/api/v1/config/tenant-llm", headers=headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["code"] == 0
    assert body["data"]["provider"] == "qwen"
    masked_map = body["data"]["api_key_masked_by_provider"]
    assert masked_map.get("deepseek")
    assert masked_map.get("qwen")

    switch_back_resp = client.put(
        "/api/v1/config/tenant-llm",
        headers=headers,
        json={
            "provider": "deepseek",
            "model": "deepseek-reasoner",
            "api_key": None,
            "base_url": "https://api.deepseek.com",
            "timeout_ms": 30000,
            "enable_thinking": False,
            "fallback_provider": "qwen",
            "fallback_model": "qwen3.5-plus",
            "extra_json": {},
            "status": 1,
        },
    )
    assert switch_back_resp.status_code == 200
    switch_back_body = switch_back_resp.json()
    assert switch_back_body["code"] == 0
    assert switch_back_body["data"]["provider"] == "deepseek"
    assert switch_back_body["data"]["api_key_masked"]


def test_tenant_search_config_persisted_in_db(client: TestClient, headers: dict):
    put_resp = client.put(
        "/api/v1/config/tenant-search-config",
        headers=headers,
        json={
            "word_w_sparse": 0.31,
            "word_w_dense": 0.69,
            "sentence_w_sparse": 0.22,
            "sentence_w_dense": 0.78,
            "top_n": 180,
            "score_gap": 0.06,
            "relative_diff": 0.1,
            "backfill_batch_size": 256,
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["code"] == 0

    get_resp = client.get("/api/v1/config/tenant-search-config", headers=headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["code"] == 0
    assert body["data"]["top_n"] == 180
    assert body["data"]["backfill_batch_size"] == 256
    assert body["data"]["word_w_sparse"] == 0.31


def test_tenant_search_config_can_update_existing_record(client: TestClient, headers: dict):
    first_resp = client.put(
        "/api/v1/config/tenant-search-config",
        headers=headers,
        json={"top_n": 180, "score_gap": 0.03, "relative_diff": 0.05},
    )
    assert first_resp.status_code == 200
    assert first_resp.json()["code"] == 0

    second_resp = client.put(
        "/api/v1/config/tenant-search-config",
        headers=headers,
        json={"top_n": 77, "score_gap": 0.11, "relative_diff": 0.22},
    )
    assert second_resp.status_code == 200
    assert second_resp.json()["code"] == 0

    get_resp = client.get("/api/v1/config/tenant-search-config", headers=headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["code"] == 0
    assert body["data"]["top_n"] == 77
    assert body["data"]["score_gap"] == 0.11
    assert body["data"]["relative_diff"] == 0.22


def test_langfuse_config_persisted_in_db(client: TestClient, headers: dict):
    put_resp = client.put(
        "/api/v1/config/observability/langfuse",
        headers=headers,
        json={
            "enabled": True,
            "public_key": "pk-lf-test",
            "secret_key": "sk-lf-test-secret",
            "host": "http://127.0.0.1:3000",
            "environment": "test",
            "release": "v-test",
            "audit_payload_max_chars": 12345,
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["code"] == 0

    get_resp = client.get("/api/v1/config/observability/langfuse", headers=headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["code"] == 0
    assert body["data"]["enabled"] is True
    assert body["data"]["public_key"] == "pk-lf-test"
    assert body["data"]["secret_key"] == ""
    assert body["data"]["secret_key_masked"]
    assert body["data"]["audit_payload_max_chars"] == 12345


def test_tenant_search_config_isolated_by_tenant(client: TestClient, headers: dict):
    tenant_a = dict(headers)
    tenant_b = dict(headers)
    tenant_b["X-Tenant-Id"] = "tenant-b"

    resp_a = client.put(
        "/api/v1/config/tenant-search-config",
        headers=tenant_a,
        json={"top_n": 123, "backfill_batch_size": 321},
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["code"] == 0

    resp_b = client.put(
        "/api/v1/config/tenant-search-config",
        headers=tenant_b,
        json={"top_n": 456, "backfill_batch_size": 654},
    )
    assert resp_b.status_code == 200
    assert resp_b.json()["code"] == 0

    get_a = client.get("/api/v1/config/tenant-search-config", headers=tenant_a)
    get_b = client.get("/api/v1/config/tenant-search-config", headers=tenant_b)
    assert get_a.status_code == 200 and get_b.status_code == 200
    assert get_a.json()["data"]["top_n"] == 123
    assert get_a.json()["data"]["backfill_batch_size"] == 321
    assert get_b.json()["data"]["top_n"] == 456
    assert get_b.json()["data"]["backfill_batch_size"] == 654


def test_active_tenant_registry_tracks_seen_tenants(client: TestClient, headers: dict):
    tenant_a = dict(headers)
    tenant_b = dict(headers)
    tenant_b["X-Tenant-Id"] = "tenant-b"

    ping_a = client.get("/api/v1/config/tenant-search-config", headers=tenant_a)
    ping_b = client.get("/api/v1/config/tenant-search-config", headers=tenant_b)
    assert ping_a.status_code == 200
    assert ping_b.status_code == 200

    list_resp = client.get("/api/v1/config/active-tenants", headers=headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["code"] == 0
    tenant_ids = {item["tenant_id"] for item in body["data"]["items"]}
    assert "tenant-a" in tenant_ids
    assert "tenant-b" in tenant_ids
