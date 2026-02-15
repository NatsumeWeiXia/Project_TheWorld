def test_capability_schema_validation(client, headers):
    resp = client.post(
        "/api/v1/ontology/capabilities",
        headers=headers,
        json={
            "code": "bad_cap",
            "name": "Bad",
            "input_schema": "not-json-schema",
            "output_schema": {"type": "object"},
        },
    )
    assert resp.status_code == 422
