def test_fewshot_retrieval_flow(client, headers):
    payload_1 = {
        "scope_type": "class",
        "scope_id": 100,
        "input_text": "按身份证号查客户",
        "output_text": "{\"action\": \"query_customer\"}",
        "tags_json": ["customer"],
    }
    payload_2 = {
        "scope_type": "class",
        "scope_id": 100,
        "input_text": "查询库存",
        "output_text": "{\"action\": \"query_inventory\"}",
        "tags_json": ["inventory"],
    }
    client.post("/api/v1/knowledge/fewshot/examples", headers=headers, json=payload_1)
    client.post("/api/v1/knowledge/fewshot/examples", headers=headers, json=payload_2)

    resp = client.get(
        "/api/v1/knowledge/fewshot/examples/search",
        headers=headers,
        params={"scope_type": "class", "scope_id": 100, "query": "身份证号", "top_k": 1},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
