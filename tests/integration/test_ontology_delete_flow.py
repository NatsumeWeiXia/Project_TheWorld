from src.app.infra.db import models
from src.app.infra.db.session import SessionLocal


def _create_class(client, headers, code, name):
    resp = client.post("/api/v1/ontology/classes", headers=headers, json={"code": code, "name": name})
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def test_delete_ontology_resources(client, headers):
    class_a = _create_class(client, headers, "device", "设备")
    class_b = _create_class(client, headers, "factory", "工厂")

    attr_resp = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "serial_no", "name": "序列号", "data_type": "string"},
    )
    assert attr_resp.status_code == 200
    attr_id = attr_resp.json()["data"]["attribute_id"]
    bind_attr_resp = client.post(
        f"/api/v1/ontology/classes/{class_a}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": [attr_id]},
    )
    assert bind_attr_resp.status_code == 200

    del_attr_resp = client.delete(f"/api/v1/ontology/data-attributes/{attr_id}", headers=headers)
    assert del_attr_resp.status_code == 200
    attrs_after_delete = client.get("/api/v1/ontology/data-attributes", headers=headers).json()["data"]["items"]
    assert all(item["id"] != attr_id for item in attrs_after_delete)

    rel_resp = client.post(
        "/api/v1/ontology/object-properties",
        headers=headers,
        json={
            "code": "located_in",
            "name": "位于",
            "relation_type": "query",
            "domain_class_ids": [class_a],
            "range_class_ids": [class_b],
        },
    )
    assert rel_resp.status_code == 200
    rel_id = rel_resp.json()["data"]["object_property_id"]
    del_rel_resp = client.delete(f"/api/v1/ontology/object-properties/{rel_id}", headers=headers)
    assert del_rel_resp.status_code == 200
    rels_after_delete = client.get("/api/v1/ontology/object-properties", headers=headers).json()["data"]["items"]
    assert all(item["id"] != rel_id for item in rels_after_delete)

    cap_resp = client.post(
        "/api/v1/ontology/capabilities",
        headers=headers,
        json={
            "code": "query_device",
            "name": "查询设备",
            "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}},
        },
    )
    assert cap_resp.status_code == 200
    cap_id = cap_resp.json()["data"]["capability_id"]
    bind_cap_resp = client.post(
        f"/api/v1/ontology/classes/{class_a}/capabilities:bind",
        headers=headers,
        json={"capability_ids": [cap_id]},
    )
    assert bind_cap_resp.status_code == 200

    del_cap_resp = client.delete(f"/api/v1/ontology/capabilities/{cap_id}", headers=headers)
    assert del_cap_resp.status_code == 200
    caps_after_delete = client.get("/api/v1/ontology/capabilities", headers=headers).json()["data"]["items"]
    assert all(item["id"] != cap_id for item in caps_after_delete)

    del_class_resp = client.delete(f"/api/v1/ontology/classes/{class_a}", headers=headers)
    assert del_class_resp.status_code == 200
    classes_after_delete = client.get("/api/v1/ontology/classes", headers=headers).json()["data"]["items"]
    assert all(item["id"] != class_a for item in classes_after_delete)

    # Physical delete: same code can be recreated after deletion.
    recreated_class = _create_class(client, headers, "device", "设备-重建")
    assert recreated_class != class_a


def test_delete_class_cleans_inheritance_even_if_tenant_mismatch(client, headers):
    class_a = _create_class(client, headers, "tenant_a_cls", "A")
    class_b = _create_class(client, headers, "tenant_b_cls", "B")

    db = SessionLocal()
    try:
        db.add(
            models.OntologyInheritance(
                tenant_id="tenant-b",
                parent_class_id=class_b,
                child_class_id=class_a,
            )
        )
        db.commit()
    finally:
        db.close()

    del_resp = client.delete(f"/api/v1/ontology/classes/{class_a}", headers=headers)
    assert del_resp.status_code == 200
