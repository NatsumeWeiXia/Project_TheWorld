# M2 API Definition

## 1. API Conventions

1. Base path: `/api/v1/reasoning`
2. Headers: `X-Tenant-Id`、`Authorization`
3. Response envelope:

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "trace_id": "trace_xxx"
}
```

## 2. Session APIs

### 2.1 Create Session

- Endpoint: `/api/v1/reasoning/sessions`
- Method: `POST`
- Summary: 创建主推理会话。
- Python File: `src/app/api/v1/reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| user_input | string | Yes | 用户输入 |
| stream | boolean | No | 是否流式 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "session_id": "sess_001", "status": "CREATED" },
  "trace_id": "trace_xxx"
}
```

### 2.2 Get Session

- Endpoint: `/api/v1/reasoning/sessions/{session_id}`
- Method: `GET`
- Summary: 获取会话状态和摘要。
- Python File: `src/app/api/v1/reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| session_id | string(path) | Yes | 会话 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "session_id": "sess_001", "status": "EXECUTING", "current_node": "execute_step" },
  "trace_id": "trace_xxx"
}
```

### 2.3 Append Message

- Endpoint: `/api/v1/reasoning/sessions/{session_id}/messages`
- Method: `POST`
- Summary: 向会话追加用户输入并触发下一轮推理。
- Python File: `src/app/api/v1/reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| session_id | string(path) | Yes | 会话 ID |
| content | string | Yes | 消息内容 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "accepted": true, "turn_id": "turn_008" },
  "trace_id": "trace_xxx"
}
```

### 2.4 Clarify Answer

- Endpoint: `/api/v1/reasoning/sessions/{session_id}:clarify`
- Method: `POST`
- Summary: 提交澄清问题答案并回流计划节点。
- Python File: `src/app/api/v1/reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| session_id | string(path) | Yes | 会话 ID |
| question_id | string | Yes | 问题 ID |
| answer | string | Yes | 用户回答 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "resumed": true, "status": "PLANNING" },
  "trace_id": "trace_xxx"
}
```

### 2.5 Cancel Session

- Endpoint: `/api/v1/reasoning/sessions/{session_id}:cancel`
- Method: `POST`
- Summary: 取消推理会话。
- Python File: `src/app/api/v1/reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| session_id | string(path) | Yes | 会话 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "session_id": "sess_001", "status": "CANCELED" },
  "trace_id": "trace_xxx"
}
```

### 2.6 Session Trace

- Endpoint: `/api/v1/reasoning/sessions/{session_id}/trace`
- Method: `GET`
- Summary: 查询会话推理链路摘要。
- Python File: `src/app/api/v1/reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| session_id | string(path) | Yes | 会话 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "session_id": "sess_001", "events": [] },
  "trace_id": "trace_xxx"
}
```

## 3. Internal API

### 3.1 Tool Select

- Endpoint: `/api/v1/internal/tool-registry:select`
- Method: `POST`
- Summary: 根据意图筛选 Top-K 工具。
- Python File: `src/app/services/tool_registry_service.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| intent | string | Yes | 意图文本 |
| candidate_scope | array[string] | No | 限定本体范围 |
| top_k | integer | No | 默认 8 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "tools": [] },
  "trace_id": "trace_xxx"
}
```

### 3.2 Parameter Extraction

- Endpoint: `/api/v1/internal/parameter-extraction:map`
- Method: `POST`
- Summary: 将非标准 Skill/MCP 入参映射为本体约束或标准 JSON Schema 入参。
- Python File: `src/app/services/parameter_extraction_service.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| source_type | string | Yes | skill/mcp/api |
| source_schema | object | Yes | 非标准输入定义 |
| user_input | string | Yes | 用户自然语言输入 |
| ontology_context | object | No | 本体上下文 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "mapped_params": {},
    "confidence": 0.92,
    "validation_passed": true
  },
  "trace_id": "trace_xxx"
}
```
