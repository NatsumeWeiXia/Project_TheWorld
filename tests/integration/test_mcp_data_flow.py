from fastapi.testclient import TestClient


def _create_class(client: TestClient, headers: dict, code: str, name: str) -> int:
    resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": code, "name": name, "description": ""},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _create_attribute(client: TestClient, headers: dict, code: str, name: str, data_type: str = "string") -> int:
    resp = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": code, "name": name, "data_type": data_type, "required": False},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["attribute_id"]


def _bind_attributes(client: TestClient, headers: dict, class_id: int, attr_ids: list[int]) -> None:
    resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/data-attributes:bind",
        headers=headers,
        json={"data_attribute_ids": attr_ids},
    )
    assert resp.status_code == 200


def test_mcp_data_query_and_group_analysis(client: TestClient, headers: dict):
    class_id = _create_class(client, headers, "order_fact", "订单事实")
    attr_region = _create_attribute(client, headers, "region", "地区", "string")
    attr_amount = _create_attribute(client, headers, "amount", "金额", "int")
    _bind_attributes(client, headers, class_id, [attr_region, attr_amount])

    create_table_resp = client.post(
        f"/api/v1/ontology/classes/{class_id}/table-binding:create-table",
        headers=headers,
    )
    assert create_table_resp.status_code == 200
    assert create_table_resp.json()["code"] == 0

    detail_resp = client.get(f"/api/v1/ontology/classes/{class_id}", headers=headers)
    detail = detail_resp.json()["data"]
    field_by_attr = {item["data_attribute_id"]: item["field_name"] for item in detail["table_binding"]["mappings"]}
    region_field = field_by_attr[attr_region]
    amount_field = field_by_attr[attr_amount]

    for row in [
        {region_field: "north", amount_field: 10},
        {region_field: "north", amount_field: 15},
        {region_field: "south", amount_field: 8},
    ]:
        ins = client.post(
            f"/api/v1/ontology/classes/{class_id}/table-binding:data",
            headers=headers,
            json={"values": row},
        )
        assert ins.status_code == 200
        assert ins.json()["code"] == 0

    query_resp = client.post(
        "/api/v1/mcp/data/query",
        headers=headers,
        json={"class_id": class_id, "filters": [], "page": 1, "page_size": 20, "sort_order": "asc"},
    )
    assert query_resp.status_code == 200
    query_data = query_resp.json()["data"]
    assert query_data["total"] >= 3

    group_resp = client.post(
        "/api/v1/mcp/data/group-analysis",
        headers=headers,
        json={
            "class_id": class_id,
            "group_by": [region_field],
            "metrics": [
                {"agg": "count", "alias": "cnt"},
                {"agg": "sum", "field": amount_field, "alias": "sum_amount"},
            ],
            "filters": [],
            "page": 1,
            "page_size": 20,
            "sort_by": "cnt",
            "sort_order": "desc",
        },
    )
    assert group_resp.status_code == 200
    group_data = group_resp.json()["data"]
    assert group_data["total"] >= 2
    assert any("cnt" in item for item in group_data["items"])
