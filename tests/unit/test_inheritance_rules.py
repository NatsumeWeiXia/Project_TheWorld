def _create_class(client, headers, code, name):
    resp = client.post("/api/v1/ontology/classes", headers=headers, json={"code": code, "name": name})
    return resp.json()["data"]["id"]


def test_inheritance_cycle_detection(client, headers):
    a = _create_class(client, headers, "a", "A")
    b = _create_class(client, headers, "b", "B")
    c = _create_class(client, headers, "c", "C")

    assert client.post(f"/api/v1/ontology/classes/{b}/inheritance", headers=headers, json={"parent_class_id": a}).status_code == 200
    assert client.post(f"/api/v1/ontology/classes/{c}/inheritance", headers=headers, json={"parent_class_id": b}).status_code == 200

    cycle_resp = client.post(f"/api/v1/ontology/classes/{a}/inheritance", headers=headers, json={"parent_class_id": c})
    assert cycle_resp.status_code == 400
    assert cycle_resp.json()["code"] == 1004
