def test_attribute_match_flow(client, headers):
    class_id = client.post(
        "/api/v1/ontology/classes", headers=headers, json={"code": "customer", "name": "客户"}
    ).json()["data"]["id"]
    attr_id = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "id_card", "name": "身份证号", "data_type": "string", "required": True},
    ).json()["data"]["attribute_id"]
    client.post(
        f"/api/v1/ontology/classes/{class_id}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_id]},
    )
    client.post(
        f"/api/v1/knowledge/attributes/{attr_id}",
        headers=headers,
        json={"definition": "用于唯一识别客户", "synonyms_json": ["证件号"]},
    )

    resp = client.post(
        "/api/v1/mcp/metadata/attributes:match",
        headers=headers,
        json={"query": "按身份证号查询客户", "top_k": 20, "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["attribute_id"] == attr_id
