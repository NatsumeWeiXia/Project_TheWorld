def test_hybrid_search_covers_all_ontology_resources(client, headers):
    cls_resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "address_entity", "name": "address entity", "description": "entity for address profile"},
    )
    assert cls_resp.status_code == 200
    class_id = cls_resp.json()["data"]["id"]

    attr_resp = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "customer_address", "name": "customer address", "data_type": "string", "description": "shipping address"},
    )
    assert attr_resp.status_code == 200

    rel_resp = client.post(
        "/api/v1/ontology/object-properties",
        headers=headers,
        json={
            "code": "has_address",
            "name": "has address",
            "description": "relation to address entity",
            "skill_md": "",
            "domain_class_ids": [class_id],
            "range_class_ids": [class_id],
        },
    )
    assert rel_resp.status_code == 200

    cap_resp = client.post(
        "/api/v1/ontology/capabilities",
        headers=headers,
        json={
            "code": "validate_address",
            "name": "validate address",
            "description": "validate address format",
            "skill_md": "",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "domain_groups": [[class_id]],
        },
    )
    assert cap_resp.status_code == 200

    search_resp = client.get(
        "/api/v1/ontology/hybrid-search",
        headers=headers,
        params={"q": "address", "types": "ontology,data-attr,obj-prop,capability", "top_k": 20},
    )
    assert search_resp.status_code == 200
    grouped = search_resp.json()["data"]["grouped"]
    assert grouped["ontology"]
    assert grouped["data-attr"]
    assert grouped["obj-prop"]
    assert grouped["capability"]


def test_graph_tools_query_uses_hybrid_search(client, headers):
    cls_resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "address_entity", "name": "address entity", "description": "entity for address profile"},
    )
    assert cls_resp.status_code == 200

    attr_resp = client.post(
        "/api/v1/ontology/data-attributes",
        headers=headers,
        json={"code": "customer_address", "name": "customer address", "data_type": "string", "description": "shipping address"},
    )
    assert attr_resp.status_code == 200

    tool_ontology_resp = client.post(
        "/api/v1/mcp/graph/tools:call",
        headers=headers,
        json={"name": "graph.list_ontologies", "arguments": {"query": "address"}},
    )
    assert tool_ontology_resp.status_code == 200
    ontologies = tool_ontology_resp.json()["data"]["content"][0]["json"]
    assert any(item["code"] == "address_entity" for item in ontologies)

    tool_attr_resp = client.post(
        "/api/v1/mcp/graph/tools:call",
        headers=headers,
        json={"name": "graph.list_data_attributes", "arguments": {"query": "address"}},
    )
    assert tool_attr_resp.status_code == 200
    attrs = tool_attr_resp.json()["data"]["content"][0]["json"]
    assert any(item["code"] == "customer_address" for item in attrs)


def test_embedding_backfill_api_batches_and_fills_storage(client, headers):
    cls_resp = client.post(
        "/api/v1/ontology/classes",
        headers=headers,
        json={"code": "bf_class", "name": "bf class", "description": "backfill class"},
    )
    assert cls_resp.status_code == 200
    class_id = cls_resp.json()["data"]["id"]

    rel_resp = client.post(
        "/api/v1/ontology/object-properties",
        headers=headers,
        json={
            "code": "bf_rel",
            "name": "bf relation",
            "description": "backfill relation",
            "skill_md": "",
            "domain_class_ids": [class_id],
            "range_class_ids": [class_id],
        },
    )
    assert rel_resp.status_code == 200

    cap_resp = client.post(
        "/api/v1/ontology/capabilities",
        headers=headers,
        json={
            "code": "bf_cap",
            "name": "bf capability",
            "description": "backfill capability",
            "skill_md": "",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "domain_groups": [[class_id]],
        },
    )
    assert cap_resp.status_code == 200

    with engine.begin() as conn:
        conn.execute(text("UPDATE ontology_class SET search_text = NULL, embedding = NULL WHERE code = 'bf_class'"))
        conn.execute(text("UPDATE ontology_relation SET search_text = NULL, embedding = NULL WHERE code = 'bf_rel'"))
        conn.execute(text("UPDATE ontology_capability SET search_text = NULL, embedding = NULL WHERE code = 'bf_cap'"))

    first = client.post(
        "/api/v1/ontology/embeddings:backfill",
        headers=headers,
        json={"resource_types": ["ontology", "obj-prop", "capability"], "batch_size": 2},
    )
    assert first.status_code == 200
    first_data = first.json()["data"]
    assert first_data["updated_total"] == 2
    assert first_data["has_more_any"] is True

    second = client.post(
        "/api/v1/ontology/embeddings:backfill",
        headers=headers,
        json={"resource_types": ["ontology", "obj-prop", "capability"], "batch_size": 2},
    )
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["updated_total"] >= 1

    with engine.connect() as conn:
        cls = conn.execute(text("SELECT search_text, embedding FROM ontology_class WHERE code = 'bf_class'")).first()
        rel = conn.execute(text("SELECT search_text, embedding FROM ontology_relation WHERE code = 'bf_rel'")).first()
        cap = conn.execute(text("SELECT search_text, embedding FROM ontology_capability WHERE code = 'bf_cap'")).first()
    assert cls is not None and cls[0] is not None and cls[1] is not None
    assert rel is not None and rel[0] is not None and rel[1] is not None
    assert cap is not None and cap[0] is not None and cap[1] is not None
from sqlalchemy import text

from src.app.infra.db.session import engine
