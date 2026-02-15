def test_owl_alignment_endpoints(client, headers):
    parent_id = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "person", "name": "人员"},
    ).json()["data"]["id"]
    class_id = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "customer", "name": "客户"},
    ).json()["data"]["id"]
    client.post(
        f"/api/v1/ontology/classes/{class_id}/inheritance",
        headers=headers,
        json={"parent_class_id": parent_id},
    )

    attr_id = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "id_card", "name": "身份证号", "data_type": "string"},
    ).json()["data"]["attribute_id"]
    bind_attr = client.post(
        f"/api/v1/ontology/classes/{class_id}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_id]},
    )
    assert bind_attr.status_code == 200

    obj_prop_id = client.post(
        "/api/v1/ontology/object-properties",
        headers=headers,
        json={
            "code": "customer_to_person",
            "name": "客户关联人员",
            "relation_type": "query",
            "domain_class_ids": [class_id],
            "range_class_ids": [parent_id],
        },
    ).json()["data"]["object_property_id"]
    assert obj_prop_id > 0

    cap_id = client.post(
        "/api/v1/ontology/capabilities",
        headers=headers,
        json={
            "code": "risk_eval",
            "name": "风险评估",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
        },
    ).json()["data"]["capability_id"]
    assert cap_id > 0
    bind_cap = client.post(
        f"/api/v1/ontology/classes/{class_id}/capabilities:bind",
        headers=headers,
        json={"capability_ids": [cap_id]},
    )
    assert bind_cap.status_code == 200

    table_binding = client.put(
        f"/api/v1/ontology/classes/{class_id}/table-binding",
        headers=headers,
        json={"table_name": "ods_customer", "table_schema": "public"},
    )
    assert table_binding.status_code == 200
    parent_binding = client.put(
        f"/api/v1/ontology/classes/{parent_id}/table-binding",
        headers=headers,
        json={"table_name": "ods_person", "table_schema": "public"},
    )
    assert parent_binding.status_code == 200

    mapping = client.put(
        f"/api/v1/ontology/classes/{class_id}/table-binding/field-mapping",
        headers=headers,
        json={"mappings": [{"data_attribute_id": attr_id, "field_name": "id_card"}]},
    )
    assert mapping.status_code == 200

    validate = client.post("/api/v1/ontology/owl:validate", headers=headers, json={"strict": True})
    assert validate.status_code == 200
    assert validate.json()["data"]["valid"] is True

    export_resp = client.get("/api/v1/ontology/owl:export?format=ttl", headers=headers)
    assert export_resp.status_code == 200
    assert "owl:Class" in export_resp.json()["data"]["content"]
