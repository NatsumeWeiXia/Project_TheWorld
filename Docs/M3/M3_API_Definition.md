# M3 API Definition

## 1. API Conventions

1. Base path: `/api/v1`
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

## 2. Data Virtualization APIs

### 2.1 Execute Query

- Endpoint: `/api/v1/data/execute-query`
- Method: `POST`
- Summary: 统一执行入口，自动路由 SQL/API 绑定。
- Python File: `src/app/api/v1/data.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| ontology_id | integer | Yes | 本体 ID |
| constraints | object | Yes | 查询约束 |
| group_by | array[string] | No | 分组字段（可选） |
| aggregations | object | No | 聚合定义（可选） |
| projection | array[string] | No | 返回字段 |
| pagination | object | No | 分页参数 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "rows": [],
    "schema": [],
    "lineage": { "route_type": "sql" },
    "next_page_token": null
  },
  "trace_id": "trace_xxx"
}
```

### 2.2 Group Analysis

- Endpoint: `/api/v1/data/group-analysis`
- Method: `POST`
- Summary: 按本体属性执行分组分析，支持 table/api 双绑定路由。
- Python File: `src/app/api/v1/data.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| ontology_id | integer | Yes | 本体 ID |
| constraints | object | No | 过滤约束 |
| group_by | array[string] | Yes | 分组字段 |
| aggregations | object | Yes | 聚合定义，如 count/sum/avg |
| pagination | object | No | 分页参数 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "groups": [],
    "schema": [],
    "lineage": { "route_type": "api" },
    "next_page_token": null
  },
  "trace_id": "trace_xxx"
}
```

## 3. Parallel Session APIs

### 3.1 Parallel Run

- Endpoint: `/api/v1/reasoning/sessions/{id}:parallel-run`
- Method: `POST`
- Summary: 拆分任务并派发子会话并行执行。
- Python File: `src/app/api/v1/parallel_reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | string(path) | Yes | 主会话 ID |
| tasks | array[object] | Yes | 子任务列表 |
| timeout_ms | integer | No | 超时控制 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "job_id": "pr_001", "sub_sessions": ["sub_1", "sub_2"] },
  "trace_id": "trace_xxx"
}
```

### 3.2 Get Artifacts

- Endpoint: `/api/v1/reasoning/sessions/{id}/artifacts`
- Method: `GET`
- Summary: 获取并行子会话回传工件。
- Python File: `src/app/api/v1/parallel_reasoning.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | string(path) | Yes | 主会话 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "artifacts": [] },
  "trace_id": "trace_xxx"
}
```

## 4. Trace APIs

### 4.1 Session Trace Tree

- Endpoint: `/api/v1/trace/sessions/{id}/tree`
- Method: `GET`
- Summary: 查询主子会话链路树。
- Python File: `src/app/api/v1/trace.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| id | string(path) | Yes | 会话 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "root_session_id": "sess_001", "children": [] },
  "trace_id": "trace_xxx"
}
```

### 4.2 Trace Spans

- Endpoint: `/api/v1/trace/spans`
- Method: `GET`
- Summary: 按 `trace_id` 查询 Span 明细。
- Python File: `src/app/api/v1/trace.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| trace_id | string(query) | Yes | 链路 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "items": [] },
  "trace_id": "trace_xxx"
}
```

### 4.3 Trace Metrics Summary

- Endpoint: `/api/v1/trace/metrics/summary`
- Method: `GET`
- Summary: 查询链路汇总指标（耗时、重试、错误率）。
- Python File: `src/app/api/v1/trace.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| time_range | string(query) | No | 时间范围 |
| session_id | string(query) | No | 会话 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "latency_p95_ms": 220, "error_rate": 0.01, "retry_rate": 0.07 },
  "trace_id": "trace_xxx"
}
```

## 5. AuthZ API

### 5.1 Policy Check

- Endpoint: `/api/v1/authz/check`
- Method: `POST`
- Summary: 对资源/动作/字段进行权限校验。
- Python File: `src/app/api/v1/authz.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| subject_id | string | Yes | 用户/角色标识 |
| resource | string | Yes | 资源名 |
| action | string | Yes | 动作 |
| fields | array[string] | No | 字段级校验 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "allowed": true, "masked_fields": ["id_no"] },
  "trace_id": "trace_xxx"
}
```
