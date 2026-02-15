# M1 API Definition

## 1. API Conventions

1. Base path: `/api/v1`
2. Headers: `X-Tenant-Id` (required), `Authorization` (required)
3. Content type: `application/json`
4. Response envelope:

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "trace_id": "trace_xxx"
}
```

## 2. Ontology APIs

### 2.0 List Ontology Classes

- Endpoint: `/api/v1/ontology/classes`
- Method: `GET`
- Summary: List ontology classes by tenant.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| status | integer(query) | No | Status filter, default `1`; pass empty for all |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "id": 1001, "code": "customer", "name": "客户", "description": "客户主本体", "status": 1 }
    ],
    "total": 1
  },
  "trace_id": "trace_xxx"
}
```

### 2.1 Create Ontology Class

- Endpoint: `/api/v1/ontology/classes`
- Method: `POST`
- Summary: Create ontology class.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| code | string | Yes | Class code (tenant unique) |
| name | string | Yes | Class name |
| description | string | No | Description |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 1001, "code": "customer", "name": "客户", "version": 1 },
  "trace_id": "trace_xxx"
}
```

### 2.2 Get Ontology Class

- Endpoint: `/api/v1/ontology/classes/{id}`
- Method: `GET`
- Summary: Get ontology class detail.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Class ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 1001, "code": "customer", "name": "客户", "description": "客户主本体", "status": 1 },
  "trace_id": "trace_xxx"
}
```

### 2.3 Update Ontology Class

- Endpoint: `/api/v1/ontology/classes/{id}`
- Method: `PUT`
- Summary: Update ontology class.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Class ID |
| name | string | No | Updated name |
| description | string | No | Updated description |
| status | integer | No | Status |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 1001, "updated": true },
  "trace_id": "trace_xxx"
}
```

### 2.4 Delete Ontology Class (Logical)

- Endpoint: `/api/v1/ontology/classes/{id}`
- Method: `DELETE`
- Summary: Logical delete ontology class.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Class ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 1001, "deleted": true },
  "trace_id": "trace_xxx"
}
```

### 2.5 Create Inheritance Link

- Endpoint: `/api/v1/ontology/classes/{id}/inheritance`
- Method: `POST`
- Summary: Create parent-child inheritance relation.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Child class ID |
| parent_class_id | integer | Yes | Parent class ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "child_class_id": 1002, "parent_class_id": 1001, "created": true },
  "trace_id": "trace_xxx"
}
```

### 2.6 Create Data Attribute

- Endpoint: `/api/v1/ontology/classes/{id}/attributes`
- Method: `POST`
- Summary: Create data attribute.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Class ID |
| code | string | Yes | Attribute code |
| name | string | Yes | Attribute name |
| data_type | string | Yes | string/int/date/boolean/json |
| required | boolean | No | Required flag |
| constraints_json | object | No | Constraints |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "attribute_id": 2001, "class_id": 1001 },
  "trace_id": "trace_xxx"
}
```

### 2.7 Create Relation

- Endpoint: `/api/v1/ontology/classes/{id}/relations`
- Method: `POST`
- Summary: Create relation.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Source class ID |
| target_class_id | integer | Yes | Target class ID |
| code | string | Yes | Relation code |
| name | string | Yes | Relation name |
| relation_type | string | Yes | transform/query |
| mcp_bindings_json | object | No | MCP bindings |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "relation_id": 3001, "source_class_id": 1001, "target_class_id": 1003 },
  "trace_id": "trace_xxx"
}
```

### 2.8 Create Capability

- Endpoint: `/api/v1/ontology/classes/{id}/capabilities`
- Method: `POST`
- Summary: Create capability.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Class ID |
| code | string | Yes | Capability code |
| name | string | Yes | Capability name |
| input_schema | object | Yes | Input JSON Schema |
| output_schema | object | Yes | Output JSON Schema |
| mcp_bindings_json | object | No | MCP bindings |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "capability_id": 4001, "class_id": 1001 },
  "trace_id": "trace_xxx"
}
```

### 2.9 Create Ontology Binding

- Endpoint: `/api/v1/ontology/classes/{id}/bindings`
- Method: `POST`
- Summary: Bind ontology class to table/api source.
- Python File: `src/app/api/v1/ontology.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | integer(path) | Yes | Class ID |
| binding_type | string | Yes | table/api |
| binding_config | object | Yes | Binding details |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "binding_id": 5001, "class_id": 1001, "binding_type": "table" },
  "trace_id": "trace_xxx"
}
```

## 3. Knowledge APIs

### 3.1 Upsert Class Knowledge

- Endpoint: `/api/v1/knowledge/classes/{class_id}`
- Method: `POST`
- Summary: Create/update class knowledge.
- Python File: `src/app/api/v1/knowledge.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| class_id | integer(path) | Yes | Class ID |
| overview | string | Yes | Overview |
| constraints_desc | string | No | Constraints |
| relation_desc | string | No | Relation description |
| capability_desc | string | No | Capability description |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "knowledge_class_id": 6001, "class_id": 1001, "version": 2 },
  "trace_id": "trace_xxx"
}
```

### 3.1.1 Get Latest Class Knowledge

- Endpoint: `/api/v1/knowledge/classes/{class_id}/latest`
- Method: `GET`
- Summary: Query latest class knowledge.
- Python File: `src/app/api/v1/knowledge.py`

### 3.2 Upsert Attribute Knowledge

- Endpoint: `/api/v1/knowledge/attributes/{attribute_id}`
- Method: `POST`
- Summary: Create/update attribute knowledge.
- Python File: `src/app/api/v1/knowledge.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| attribute_id | integer(path) | Yes | Attribute ID |
| definition | string | Yes | Definition |
| synonyms_json | array[string] | No | Synonyms |
| constraints_desc | string | No | Constraints |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "knowledge_attribute_id": 7001, "attribute_id": 2001, "version": 1 },
  "trace_id": "trace_xxx"
}
```

### 3.2.1 Get Latest Attribute Knowledge

- Endpoint: `/api/v1/knowledge/attributes/{attribute_id}/latest`
- Method: `GET`
- Summary: Query latest attribute knowledge.
- Python File: `src/app/api/v1/knowledge.py`

### 3.3 Create Relation Template

- Endpoint: `/api/v1/knowledge/relations/{relation_id}/templates`
- Method: `POST`
- Summary: Create relation template.
- Python File: `src/app/api/v1/knowledge.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| relation_id | integer(path) | Yes | Relation ID |
| prompt_template | string | Yes | Prompt template |
| template_schema | object | Yes | Template schema |
| mcp_slots_json | object | No | MCP slot config |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "template_id": 8001, "relation_id": 3001, "version": 1 },
  "trace_id": "trace_xxx"
}
```

### 3.3.1 Get Latest Relation Template

- Endpoint: `/api/v1/knowledge/relations/{relation_id}/templates/latest`
- Method: `GET`
- Summary: Query latest relation template.
- Python File: `src/app/api/v1/knowledge.py`

### 3.4 Create Capability Template

- Endpoint: `/api/v1/knowledge/capabilities/{capability_id}/templates`
- Method: `POST`
- Summary: Create capability template.
- Python File: `src/app/api/v1/knowledge.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| capability_id | integer(path) | Yes | Capability ID |
| prompt_template | string | Yes | Prompt template |
| template_schema | object | Yes | Template schema |
| mcp_slots_json | object | No | MCP slot config |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "template_id": 9001, "capability_id": 4001, "version": 1 },
  "trace_id": "trace_xxx"
}
```

### 3.4.1 Get Latest Capability Template

- Endpoint: `/api/v1/knowledge/capabilities/{capability_id}/templates/latest`
- Method: `GET`
- Summary: Query latest capability template.
- Python File: `src/app/api/v1/knowledge.py`

### 3.5 Create Few-shot Example

- Endpoint: `/api/v1/knowledge/fewshot/examples`
- Method: `POST`
- Summary: Create few-shot sample.
- Python File: `src/app/api/v1/knowledge.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| scope_type | string | Yes | class/attr/relation/capability |
| scope_id | integer | Yes | Scope ID |
| input_text | string | Yes | Input sample |
| output_text | string | Yes | Output sample |
| tags_json | object | No | Tags metadata |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "example_id": 10001, "queued_for_embedding": true },
  "trace_id": "trace_xxx"
}
```

### 3.6 Search Few-shot Examples

- Endpoint: `/api/v1/knowledge/fewshot/examples/search`
- Method: `GET`
- Summary: Search few-shot examples.
- Python File: `src/app/api/v1/knowledge.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| scope_type | string(query) | Yes | class/attr/relation/capability |
| scope_id | integer(query) | Yes | Scope ID |
| query | string(query) | Yes | Query text |
| top_k | integer(query) | No | Default 5 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "example_id": 10001, "input_text": "按身份证号查询客户", "output_text": "{...}", "score": 0.91 }
    ]
  },
  "trace_id": "trace_xxx"
}
```

### 3.7 List Few-shot Examples

- Endpoint: `/api/v1/knowledge/fewshot/examples`
- Method: `GET`
- Summary: List few-shot examples by scope.
- Python File: `src/app/api/v1/knowledge.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| scope_type | string(query) | Yes | class/attr/relation/capability |
| scope_id | integer(query) | Yes | Scope ID |

## 4. Metadata MCP APIs

### 4.1 Match Data Attributes

- Endpoint: `/api/v1/mcp/metadata/attributes:match`
- Method: `POST`
- Summary: Match attributes with hybrid retrieval.
- Python File: `src/app/api/v1/mcp_metadata.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| query | string | Yes | Query text |
| filters | object | No | Domain filter |
| top_k | integer | No | Default 20 |
| page | integer | No | Default 1 |
| page_size | integer | No | Default 20 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "attribute_id": 2001, "name": "身份证号", "score": 0.95, "class_refs": [1001], "knowledge_summary": "用于唯一识别客户" }
    ],
    "page": 1,
    "page_size": 20
  },
  "trace_id": "trace_xxx"
}
```

### 4.2 Query Ontologies by Attributes

- Endpoint: `/api/v1/mcp/metadata/ontologies:by-attributes`
- Method: `POST`
- Summary: Query ontology classes by attribute IDs.
- Python File: `src/app/api/v1/mcp_metadata.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| attribute_ids | array[integer] | Yes | Attribute IDs |
| top_k | integer | No | Default 20 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "class_id": 1001, "name": "客户", "match_strength": 0.89, "matched_attributes": [2001, 2002], "knowledge_summary": "客户主数据" }
    ]
  },
  "trace_id": "trace_xxx"
}
```

### 4.3 Get Ontology Detail

- Endpoint: `/api/v1/mcp/metadata/ontologies/{class_id}`
- Method: `GET`
- Summary: Get ontology detail.
- Python File: `src/app/api/v1/mcp_metadata.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| class_id | integer(path) | Yes | Class ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "class": { "id": 1001, "name": "客户", "knowledge_summary": "客户本体" },
    "attributes": [],
    "relations": [],
    "capabilities": [],
    "bindings": []
  },
  "trace_id": "trace_xxx"
}
```

### 4.4 Get Relation/Capability Execution Detail

- Endpoint: `/api/v1/mcp/metadata/execution/{type}/{id}`
- Method: `GET`
- Summary: Get execution detail for relation/capability.
- Python File: `src/app/api/v1/mcp_metadata.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| type | string(path) | Yes | relation/capability |
| id | integer(path) | Yes | Relation/Capability ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 3001,
    "type": "relation",
    "execution_desc": "根据客户标识查询账户",
    "prompt_template": "...",
    "mcp_bindings": [],
    "input_schema": {},
    "output_schema": {}
  },
  "trace_id": "trace_xxx"
}
```

## 5. Console Page

### 5.1 M1 Ontology/Knowledge Console

- Endpoint: `/m1/console`
- Method: `GET`
- Summary: Web page for ontology, data attribute, relation, capability, binding and knowledge entry/management.
- Python File: `src/app/main.py` + `src/app/ui/m1_console.html`

## 6. 需求 1.3/1.6 对齐补充 API（优先级覆盖前文冲突）

说明：如与前文冲突，以本节为准。

1. OWL 与标准化
- `POST /api/v1/ontology/owl:validate`：校验本体模型是否符合 OWL 约束。
- `GET /api/v1/ontology/owl:export`：导出当前租户 OWL 文件（RDF/XML 或 TTL）。

2. 本体树与目录化管理
- `GET /api/v1/ontology/tree`：获取本体树（父子结构）。
- `POST /api/v1/ontology/classes/{id}/parent`：调整父节点。
- `GET /api/v1/ontology/data-attributes`：全量数据属性列表（全局目录）。
- `GET /api/v1/ontology/object-properties`：全量对象属性列表（全局目录）。
- `GET /api/v1/ontology/capabilities`：全量本体能力列表（可独立存在）。

3. 本体引用关系配置
- `POST /api/v1/ontology/classes/{id}/data-attributes:bind`：为本体绑定数据属性引用。
- `POST /api/v1/ontology/classes/{id}/object-properties:bind`：为本体绑定对象属性引用。
- `POST /api/v1/ontology/classes/{id}/capabilities:bind`：为本体绑定能力引用。

4. 本体关联表配置（One-Class-One-Table）
- `PUT /api/v1/ontology/classes/{id}/table-binding`：设置本体唯一关联表。
- `PUT /api/v1/ontology/classes/{id}/table-binding/field-mapping`：设置数据属性到字段映射。

5. 知识框架结构化接口（对齐 1.3）
- 对象属性知识与能力知识写入接口需强制字段：
  - `intent_desc`
  - `few_shot_examples`
  - `json_schema`
  - `skill_md`
  - `prompt_template`
  - `mcp_bindings`
- 元数据详情接口返回上述结构化字段，保障 2.1/2.2 推理可执行性。
