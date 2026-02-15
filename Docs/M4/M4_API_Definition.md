# M4 API Definition

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

## 2. Retrieval APIs

### 2.1 Retrieval Search

- Endpoint: `/api/v1/retrieval/search`
- Method: `POST`
- Summary: 多路召回 + 融合 + 可选重排。
- Python File: `src/app/api/v1/retrieval.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| query | string | Yes | 查询文本 |
| top_k | integer | No | 默认 20 |
| enable_graph | boolean | No | 启用图检索 |
| enable_rerank | boolean | No | 启用重排 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "items": [], "evidence_paths": [] },
  "trace_id": "trace_xxx"
}
```

### 2.2 Retrieval Route

- Endpoint: `/api/v1/retrieval/route`
- Method: `POST`
- Summary: 返回路由策略决策结果。
- Python File: `src/app/api/v1/retrieval.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| query | string | Yes | 查询文本 |
| budget_ms | integer | No | 延时预算 |
| intent_type | string | No | 查询意图 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "route": "hybrid", "weights": { "sparse": 0.3, "dense": 0.4, "graph": 0.3 }, "enable_rerank": true },
  "trace_id": "trace_xxx"
}
```

### 2.3 Retrieval Rerank

- Endpoint: `/api/v1/retrieval/rerank`
- Method: `POST`
- Summary: 对候选集合执行重排。
- Python File: `src/app/api/v1/retrieval.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| query | string | Yes | 查询文本 |
| candidates | array[object] | Yes | 候选集合 |
| top_k | integer | No | 默认 20 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "items": [] },
  "trace_id": "trace_xxx"
}
```

### 2.4 Retrieval Explain

- Endpoint: `/api/v1/retrieval/explain/{request_id}`
- Method: `GET`
- Summary: 返回路由、召回、重排证据。
- Python File: `src/app/api/v1/retrieval.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| request_id | string(path) | Yes | 请求 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "router_decision": {}, "recall_sources": [], "rerank_scores": [] },
  "trace_id": "trace_xxx"
}
```

## 3. Evaluation APIs

### 3.1 Create Eval Job

- Endpoint: `/api/v1/eval/jobs`
- Method: `POST`
- Summary: 提交检索评估任务。
- Python File: `src/app/api/v1/eval.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| dataset_id | string | Yes | 数据集 ID |
| strategy_version | string | Yes | 策略版本 |
| metrics | array[string] | Yes | 指标列表 |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "job_id": "eval_001", "status": "PENDING" },
  "trace_id": "trace_xxx"
}
```

### 3.2 Get Eval Job

- Endpoint: `/api/v1/eval/jobs/{job_id}`
- Method: `GET`
- Summary: 查询评估任务状态与结果摘要。
- Python File: `src/app/api/v1/eval.py`
- Request Parameters:

| Name | Type | Required | Description |
|---|---|---:|---|
| job_id | string(path) | Yes | 任务 ID |

- Response Schema (JSON):

```json
{
  "code": 0,
  "message": "ok",
  "data": { "job_id": "eval_001", "status": "SUCCESS", "metrics": { "recall@20": 0.82, "mrr": 0.68 } },
  "trace_id": "trace_xxx"
}
```
