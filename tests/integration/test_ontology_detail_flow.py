def _create_class(client, headers, code, name):
    return client.post("/api/v1/ontology/classes", headers=headers, json={"code": code, "name": name}).json()["data"]["id"]


def test_ontology_detail_inheritance_merge(client, headers):
    parent = _create_class(client, headers, "person", "人员")
    child = _create_class(client, headers, "customer", "客户")
    attr_id = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "name", "name": "姓名", "data_type": "string"},
    ).json()["data"]["attribute_id"]
    client.post(
        f"/api/v1/ontology/classes/{parent}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_id]},
    )
    client.post(
        f"/api/v1/ontology/classes/{child}/inheritance",
        headers=headers,
        json={"parent_class_id": parent},
    )

    resp = client.get(f"/api/v1/mcp/metadata/ontologies/{child}", headers=headers)
    assert resp.status_code == 200
    attrs = resp.json()["data"]["attributes"]
    assert len(attrs) == 1
    assert attrs[0]["inherited"] is True
