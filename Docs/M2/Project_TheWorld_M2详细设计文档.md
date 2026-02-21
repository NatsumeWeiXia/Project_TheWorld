# Project_TheWorld M2 详细设计文档（按当前实现更新）

## 1. 文档目标

本文档描述 M2 在当前代码中的实际落地形态，覆盖：

1. 推理会话主链路（LangGraph + LangChain）。
2. 会话上下文与链路审计（DB Trace + Langfuse Sink）。
3. Graph Chat 与 MCP Data 的联动执行。
4. Global Config 中与 M2 相关的租户级配置持久化能力。

---

## 2. 当前落地范围

### 2.1 已实现（In Scope）

1. `reasoning` 会话 API（create/get/run/clarify/trace/cancel）。
2. LangGraph 串行节点编排：意图解析 -> 属性匹配 -> 本体定位 -> 任务规划 -> 执行 -> 收敛。
3. 澄清机制（无属性/无本体/无能力/空任务）。
4. 数据执行能力：`mcp.data.query` / `mcp.data.group_analysis`。
5. 会话上下文持久化（`global/session/local/artifact`）。
6. 事件化链路审计（`reasoning_trace_event`）与 Graph 页 Audit 可视化。
7. Langfuse 可选下沉（开启配置后同步上报审计事件）。
8. 租户 LLM 配置、租户搜索配置的数据库持久化。
9. 激活租户登记（`active_tenant`）与查询接口。

### 2.2 未实现（Out of Scope）

1. 多子会话并行编排。
2. 通用 Text-to-SQL/跨源数据虚拟化路由。
3. 完整可观测三件套（metrics/span/log）统一平台化治理。

---

## 3. 代码结构与调用链

### 3.1 核心模块

1. API：
   - `src/app/api/v1/reasoning.py`
   - `src/app/api/v1/mcp_data.py`
   - `src/app/api/v1/config.py`
2. Service：
   - `src/app/services/reasoning_service.py`
   - `src/app/services/context_service.py`
   - `src/app/services/trace_service.py`
   - `src/app/services/mcp_data_service.py`
   - `src/app/services/tenant_llm_config_service.py`
   - `src/app/services/tenant_runtime_config_service.py`
   - `src/app/services/observability/langfuse_sink.py`
3. Repository：
   - `src/app/repositories/reasoning_repo.py`
   - `src/app/repositories/config_repo.py`
4. Schema：
   - `src/app/schemas/reasoning.py`
   - `src/app/schemas/mcp_data.py`
   - `src/app/schemas/config.py`

### 3.2 请求调用链（run）

```mermaid
flowchart LR
U[Client/Graph Chat] --> R1[/POST reasoning run/]
R1 --> RS[ReasoningService]
RS --> LG[LangGraph StateGraph]
LG --> MM[MCPMetadataService]
LG --> MD[MCPDataService]
LG --> LC[LangChainLLMClient]
RS --> TS[TraceService]
RS --> CS[ContextService]
TS --> DB[(reasoning_trace_event)]
TS --> LF[LangfuseSink(Optional)]
CS --> DB
```

---

## 4. Reasoning API（实际实现）

前缀：`/api/v1/reasoning`

1. `POST /sessions`
   - 入参：`user_input`、`metadata`
   - 动作：创建 `reasoning_session` + 首轮 `reasoning_turn`，写入初始 trace。
2. `GET /sessions/{session_id}`
   - 返回会话状态、latest turn、pending clarification、当前 turn 任务列表。
3. `POST /sessions/{session_id}/run`
   - 若存在 pending clarification，直接返回 `waiting_clarification`。
   - 否则执行 LangGraph 主链路并返回 `completed` 或 `waiting_clarification`。
4. `POST /sessions/{session_id}/clarify`
   - 将 pending clarification 置为 answered，回写 turn 输入并恢复会话为 `created`。
5. `GET /sessions/{session_id}/trace`
   - 返回 `reasoning_trace_event` 时间序列。
6. `POST /sessions/{session_id}/cancel`
   - 会话标记 `cancelled`，并记录失败类 trace（reason=cancelled_by_user 或传入 reason）。

---

## 5. 状态机与节点

### 5.1 会话状态（实际出现）

1. `created`
2. `understanding`
3. `waiting_clarification`
4. `completed`
5. `failed`
6. `cancelled`

### 5.2 LangGraph 节点（`ReasoningService`）

1. `parse_intent`
2. `match_attributes`
3. `locate_ontologies`
4. `plan_tasks`
5. `execute`
6. `finalize`

节点间通过 `_use_clarification_path` 判断是否提前结束为澄清分支。

---

## 6. 数据执行策略（MCP Data）

`execute` 节点当前策略：

1. 默认执行 `mcp.data.query`。
2. 当 query 命中关键词（如“分组/统计/group/count/sum/avg/平均”）时执行 `mcp.data.group_analysis`。
3. group-analysis 依赖本体字段映射，缺失映射时抛出校验错误并进入失败路径。

---

## 7. 审计与可观测

### 7.1 Trace 事件类型（白名单）

1. `intent_parsed`
2. `attributes_matched`
3. `ontologies_located`
4. `task_planned`
5. `task_executed`
6. `clarification_asked`
7. `recovery_triggered`
8. `session_completed`
9. `session_failed`
10. `session_started`
11. `mcp_call_requested`
12. `mcp_call_completed`
13. `llm_prompt_sent`
14. `llm_response_received`

非白名单事件会被归一为 `session_failed` 并保留 `raw_event_type`。

### 7.2 双写策略

1. 主存储：`reasoning_trace_event`（DB）。
2. 可选下沉：Langfuse（由 `observability/langfuse` 配置控制）。
3. Graph 页通过 `GET /api/v1/reasoning/sessions/{session_id}/trace` 展示 Audit Timeline。

---

## 8. 数据模型（当前数据库）

### 8.1 Reasoning 相关表

1. `reasoning_session`
2. `reasoning_turn`
3. `reasoning_task`
4. `reasoning_context`
5. `reasoning_trace_event`
6. `reasoning_clarification`

索引由 ORM/迁移创建，主要为：

1. `reasoning_session.tenant_id`
2. `reasoning_turn.session_id` + 唯一约束 `(session_id, turn_no)`
3. `reasoning_task.session_id/turn_id/status`
4. `reasoning_context.session_id/scope/key`
5. `reasoning_trace_event.session_id/turn_id/step/event_type/trace_id`
6. `reasoning_clarification.session_id/turn_id/status`

### 8.2 Config/租户相关表（与 M2 运行强关联）

1. `tenant_llm_config`
   - 按 tenant 保存 provider/model/base_url/timeout/api_key_cipher 等。
   - 支持 provider 级 API Key 隔离存储（加密后存储）。
2. `tenant_runtime_config`
   - `search_config` 下保存租户级检索参数：
     - `word_w_sparse/word_w_dense`
     - `sentence_w_sparse/sentence_w_dense`
     - `top_n/score_gap/relative_diff`
     - `backfill_batch_size`
3. `system_runtime_config`
   - 保存系统级配置（如 Langfuse 运行参数）。
4. `active_tenant`
   - 记录触达 API 的租户：`tenant_id/is_active/first_seen_at/last_seen_at`。

---

## 9. Config API（当前实现）

前缀：`/api/v1/config`

1. `GET/PUT /tenant-llm`
2. `POST /tenant-llm:verify`
3. `GET/PUT /tenant-search-config`
4. `GET/PUT /observability/langfuse`
5. `GET /active-tenants`

说明：

1. `tenant-search-config` 已作为 Graph/Console 检索参数的真实来源。
2. 中间件会在 API 请求携带 `X-Tenant-Id` 时自动 touch `active_tenant`。

---

## 10. 迁移与兼容策略

当前迁移：

1. `20260218_0001`：M1 baseline
2. `20260219_0002`：reasoning 相关表
3. `20260219_0003`：tenant_llm_config
4. `20260219_0004`：active_tenant

兼容说明：

1. `20260219_0002~0004` 已实现幂等创建（存在则跳过），兼容历史环境先建表后迁移的场景。
2. 服务启动仍保留 `_ensure_runtime_schema` 做少量兼容补列。

---

## 11. 测试覆盖（当前）

1. `tests/integration/test_reasoning_session_flow.py`
   - 覆盖 create/run/clarify/trace 基本流程。
2. `tests/integration/test_mcp_data_flow.py`
   - 覆盖 query/group-analysis。
3. `tests/integration/test_tenant_llm_config_flow.py`
   - 覆盖 tenant-llm、tenant-search-config、langfuse config、active-tenants。
4. `tests/unit/test_llm_provider_factory.py`
   - 覆盖 LLM provider factory 路由与构建。

---

## 12. M2 完成定义（按当前代码）

1. reasoning 主链路可运行并可审计。
2. 澄清流程可闭环。
3. MCP Data 能力已接入执行节点。
4. 审计事件可在 DB 查询，并可选同步到 Langfuse。
5. 租户级 LLM/检索配置可持久化并参与运行时行为。
