from urllib.parse import quote


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


def test_ontology_resource_detail_and_update_endpoints(client, headers):
    class_a = _create_class(client, headers, "device2", "设备2")
    class_b = _create_class(client, headers, "factory2", "工厂2")

    attr_resp = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "serial2", "name": "序列号2", "data_type": "string"},
    )
    assert attr_resp.status_code == 200
    attr_id = attr_resp.json()["data"]["attribute_id"]

    rel_resp = client.post(
        "/api/v1/ontology/object-properties",
        headers=headers,
        json={
            "code": "located_in2",
            "name": "位于2",
            "relation_type": "query",
            "domain_class_ids": [class_a],
            "range_class_ids": [class_b],
        },
    )
    assert rel_resp.status_code == 200
    rel_id = rel_resp.json()["data"]["object_property_id"]

    cap_resp = client.post(
        "/api/v1/ontology/capabilities",
        headers=headers,
        json={
            "code": "query_device2",
            "name": "查询设备2",
            "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}},
        },
    )
    assert cap_resp.status_code == 200
    cap_id = cap_resp.json()["data"]["capability_id"]

    get_attr_resp = client.get(f"/api/v1/ontology/data-attributes/{attr_id}", headers=headers)
    assert get_attr_resp.status_code == 200
    assert get_attr_resp.json()["data"]["id"] == attr_id
    put_attr_resp = client.put(
        f"/api/v1/ontology/data-attributes/{attr_id}",
        headers=headers,
        json={"name": "序列号2-更新", "description": "updated"},
    )
    assert put_attr_resp.status_code == 200

    get_rel_resp = client.get(f"/api/v1/ontology/object-properties/{rel_id}", headers=headers)
    assert get_rel_resp.status_code == 200
    assert get_rel_resp.json()["data"]["id"] == rel_id
    put_rel_resp = client.put(
        f"/api/v1/ontology/object-properties/{rel_id}",
        headers=headers,
        json={
            "name": "位于2-更新",
            "description": "updated",
            "domain_class_ids": [class_a],
            "range_class_ids": [class_b],
        },
    )
    assert put_rel_resp.status_code == 200

    get_cap_resp = client.get(f"/api/v1/ontology/capabilities/{cap_id}", headers=headers)
    assert get_cap_resp.status_code == 200
    assert get_cap_resp.json()["data"]["id"] == cap_id
    put_cap_resp = client.put(
        f"/api/v1/ontology/capabilities/{cap_id}",
        headers=headers,
        json={"name": "查询设备2-更新", "description": "updated"},
    )
    assert put_cap_resp.status_code == 200


def test_create_table_by_ontology_and_backfill_mapping(client, headers):
    class_resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "memento_customer", "name": "纪念体客户"},
    )
    assert class_resp.status_code == 200
    class_id = class_resp.json()["data"]["id"]

    attr_name = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "name", "name": "姓名", "data_type": "string"},
    ).json()["data"]["attribute_id"]
    attr_tags = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "tags", "name": "标签", "data_type": "array"},
    ).json()["data"]["attribute_id"]

    bind_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_name, attr_tags]},
    )
    assert bind_resp.status_code == 200

    create_table_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:create-table",
        headers=headers,
    )
    assert create_table_resp.status_code == 200
    table_data = create_table_resp.json()["data"]
    assert table_data["table_name"] == "t_memento_memento_customer"
    assert len(table_data["field_mappings"]) == 2

    detail_resp = client.get(f"/api/v1/ontology/classes/{class_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert detail_data["table_binding"]["table_name"] == "t_memento_memento_customer"
    mapping_fields = {item["field_name"] for item in detail_data["table_binding"]["mappings"]}
    assert "name" in mapping_fields
    assert "tags" in mapping_fields


def test_manage_entity_data_query_create_update(client, headers):
    class_id = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "entity_manage", "name": "实体管理"},
    ).json()["data"]["id"]
    attr_name = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "name", "name": "名称", "data_type": "string"},
    ).json()["data"]["attribute_id"]
    attr_age = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "age", "name": "年龄", "data_type": "int"},
    ).json()["data"]["attribute_id"]
    client.post(
        f"/api/v1/ontology/classes/{class_id}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_name, attr_age]},
    )
    client.post(f"/api/v1/ontology/classes/{class_id}/table-binding:create-table", headers=headers)

    create_row_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:data",
        headers=headers,
        json={"values": {"name": "Alice", "age": 18}},
    )
    assert create_row_resp.status_code == 200

    query_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:data:query",
        headers=headers,
        json={"page": 1, "page_size": 20, "filters": [{"field": "name", "op": "eq", "value": "Alice"}], "sort_field": "age", "sort_order": "desc"},
    )
    assert query_resp.status_code == 200
    query_data = query_resp.json()["data"]
    assert query_data["total"] >= 1
    row = query_data["items"][0]
    assert row["name"] == "Alice"
    row_token = row["__row_token"]

    update_row_resp = client.put(
        f"/api/v1/ontology/classes/{class_id}/table-binding:data/{quote(str(row_token), safe='')}",
        headers=headers,
        json={"values": {"age": 20}},
    )
    assert update_row_resp.status_code == 200

    query_after_update = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:data:query",
        headers=headers,
        json={"page": 1, "page_size": 20, "filters": [{"field": "name", "op": "eq", "value": "Alice"}]},
    )
    assert query_after_update.status_code == 200
    updated_row = query_after_update.json()["data"]["items"][0]
    assert updated_row["age"] == 20
