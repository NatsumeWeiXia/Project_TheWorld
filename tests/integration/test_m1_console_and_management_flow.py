def test_m1_console_page_accessible(client):
    resp = client.get("/m1/console")
    assert resp.status_code == 200
    assert "本体管理台" in resp.text


def test_list_classes_and_latest_knowledge(client, headers):
    create_resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "customer", "name": "客户", "description": "客户主本体"},
    )
    assert create_resp.status_code == 200
    class_id = create_resp.json()["data"]["id"]

    list_resp = client.get("/api/v1/ontology/classes", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["data"]["total"] >= 1

    upsert_k_resp = client.post(
        f"/api/v1/knowledge/classes/{class_id}",
        headers=headers,
        json={
            "overview": "客户知识概述",
            "constraints_desc": "约束",
            "relation_desc": "关系",
            "capability_desc": "能力",
        },
    )
    assert upsert_k_resp.status_code == 200

    latest_resp = client.get(f"/api/v1/knowledge/classes/{class_id}/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["data"]["overview"] == "客户知识概述"
