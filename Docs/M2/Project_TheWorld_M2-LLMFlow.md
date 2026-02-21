# Graph Chat 后台处理流程与 LLM 交互说明（对齐当前实现）

## 1. 入口与调用链

1. 前端 `src/app/ui/graph_workspace.html`
   - 首次消息：`POST /api/v1/reasoning/sessions`
   - 执行：`POST /api/v1/reasoning/sessions/{session_id}/run`
   - 待澄清：`POST /api/v1/reasoning/sessions/{session_id}/clarify` 后再次 `run`
2. API 层：`src/app/api/v1/reasoning.py`
3. 编排层：`src/app/services/reasoning_service.py`（LangGraph）
4. Graph Tool 层：`src/app/services/graph_tool_agent.py`
5. 执行器层：`src/app/services/reasoning_executors.py`
6. LLM 层：`src/app/services/llm/langchain_client.py`

## 2. 状态机（LangGraph）

当前节点：

`understand_intent -> discover_candidates -> select_anchor_ontologies -> inspect_ontology -> execute -> finalize`

分支要点：

1. `waiting_clarification`：信息不足或无法确定可执行目标。
2. `completed`：完成执行并输出结构化结果。
3. `failed`：LLM 或执行阶段异常（不再回退）。

## 3. 节点说明

### 3.1 understand_intent

使用 LLM 进行结构化意图抽取：

1. 输入：用户 query。
2. 输出：
   - `keywords`
   - `business_elements`
   - `goal_actions`
   - `intent_summary`
3. 失败策略：LLM 异常直接抛错并结束本轮。

实现位置：`src/app/services/reasoning_service.py` 的 `_node_understand_intent`。

### 3.2 discover_candidates

1. 使用 `query + 关键词 + 业务要素` 组装多轮检索词。
2. MCP Graph 调用：
   - `graph.list_data_attributes`
   - `graph.get_data_attribute_related_ontologies`
   - `graph.list_ontologies`
3. 聚合策略：
   - 按 `code` 去重（保留最高分）
   - 按 score 降序排序
4. 关键优化：
   * 来自 `graph.get_data_attribute_related_ontologies` 的候选本体分值按命中属性数累加，每命中 1 个属性 `+0.1`（不再固定分值）。

实现位置：`_node_discover_candidates` 与 `_merge_scored_items`。

### 3.3 select_anchor_ontologies

使用 LLM 从候选本体中选择：

1. 输入锚点本体：不可为空，可多个（`input_ontology_codes`）。
2. 目标本体：可为空（`target_ontology_codes`）。
3. 同步记录 `selection_reason` 到 `plan_state`。

实现位置：`_node_select_anchor_ontologies`。

### 3.4 inspect_ontology（重点）

#### 3.4.1 业务目标

在当前锚点本体上，先做“选什么执行”的决策，不直接进入细节执行。

决策对象二选一：

1. 执行某个 `capability`。
2. 执行某个 `object_property`（进入关系驱动执行路径）。

#### 3.4.2 决策上下文（轻上下文）

本节点给 LLM 的判断上下文仅包含：

1. 用户 query / intent。
2. 当前本体信息。
3. `graph.get_ontology_details` 返回中 capability 与 object_property 的：
   - `code`
   - `name`
   - `description`

说明：本节点不把 capability/object_property 的 details 全量作为决策输入，避免在决策阶段注入执行细节。

#### 3.4.3 决策结果与后续动作

LLM 返回结构化决策：

1. `action=execute_capability` + `capability_code`。
2. `action=execute_object_property` + `object_property_code`。

随后进入“重上下文”加载：

1. 若选 capability：调用 `graph.get_capability_details`，把详情写入 `selected_capability_detail`。
2. 若选 object_property：调用 `graph.get_object_property_details`，把详情写入 `selected_object_property_detail`。

这些 details 不用于“是否执行”的判断，而用于下一节点的实际执行规划。

#### 3.4.4 产物落盘（状态）

本节点产出并传递给执行阶段：

1. `selected_capability` / `selected_capability_detail`。
2. `selected_object_property` / `selected_object_property_detail`。
3. `plan_state.execution_decision`（保留 action/code/reason）。

并发出 `task_planned` 事件（计入 Audit/Langfuse）。

实现位置：`src/app/services/reasoning_service.py` 的 `_node_inspect_ontology`。

### 3.5 execute（基于执行器抽象，重点）

#### 3.5.1 设计目标

将“决策”和“执行”彻底分层：

1. inspect 只负责选中资源。
2. execute 只负责基于资源详情规划并执行动作。

#### 3.5.2 执行器抽象

新增抽象与默认实现：

1. `CapabilityExecutor` / `LLMCapabilityExecutor`。
2. `ObjectPropertyExecutor` / `LLMObjectPropertyExecutor`。

代码位置：`src/app/services/reasoning_executors.py`。

#### 3.5.3 通用执行流程

`_node_execute` 的统一流程：

1. 根据 inspect 结果创建 `reasoning_task`（`task_type=capability|object_property`）。
2. 组装执行上下文：
   - 当前本体、选中资源、资源 details
   - attribute catalog（包含 attribute code/name 与 field_name 映射）
   - LLM 决策函数与 MCP Data 调用包装函数
3. 调用对应执行器执行。
4. 写回：
   - `data_execution_mode`
   - `data_execution`
   - `plan_state.executor`
   - task 状态 `completed`

#### 3.5.4 CapabilityExecutor 业务与实现

输入：当前本体 + capability details + 用户意图。

步骤：

1. 由 LLM 生成数据执行计划（JSON）：
   - `mode=query|group-analysis`
   - `filters`
   - `group_by`
   - `metrics`
   - 排序/分页参数
2. 执行器标准化计划并落地调用：
   - `mcp.data.query`
   - 或 `mcp.data.group-analysis`

当用户输入携带明确值（如手机号）时，LLM 应将值写入 `filters`，再由执行器映射到本体字段执行。

#### 3.5.5 ObjectPropertyExecutor 业务与实现

输入：当前本体 + object_property details + 用户意图。

步骤：

1. 基于 object_property 的 `domain/range` 计算可达目标本体候选。
2. 由 LLM 决定 `target_ontology_code` 与数据执行计划。
3. 解析目标本体并构建其 attribute catalog。
4. 对目标本体执行 `mcp.data.query` 或 `mcp.data.group-analysis`。

该路径支持“关系驱动到目标本体后再取数”的执行模型。

实现位置：`src/app/services/reasoning_service.py` 的 `_node_execute` 与 `src/app/services/reasoning_executors.py`。

### 3.6 finalize

1. 调用 LLM 生成摘要（`summarize_with_context`）。
2. 输出包含：
   - `orchestration_framework`
   - `llm_framework`
   - `llm_route`
   - `planning`
   - `data_execution_mode`
   - `data_execution`
3. 失败策略：不回退固定摘要，LLM 异常直接失败。

## 4. 审计与可观测约束落实

约束：所有 LLM 交互与 MCP 调用都必须可审计并下沉 Langfuse。

当前已落实：

1. MCP Graph 调用经 `_graph_call` 记录：
   - `mcp_call_requested`
   - `mcp_call_completed`
2. MCP Data 调用经 `_mcp_data_call` 记录：
   - `mcp_call_requested`（`method=mcp.data.query|mcp.data.group-analysis`）
   - `mcp_call_completed`
3. LLM 调用统一记录：
   - `llm_prompt_sent`
   - `llm_response_received`
4. 所有事件通过 `TraceService.emit`：
   - 写入 `reasoning_trace_event`
   - 同步推送 Langfuse
5. Graph 页 `Audit` 读取 `GET /api/v1/reasoning/sessions/{session_id}/trace`。

## 5. 前端 Graph Chat 协议

1. 待澄清：`awaitingClarification`。
2. 澄清提交：
   - `answer.type=clarification`

## 6. 测试对齐

`tests/integration/test_reasoning_session_flow.py`：

1. `test_reasoning_run_completed_flow`
2. `test_reasoning_clarification_flow`
3. `test_reasoning_object_property_execute_flow`
4. `test_reasoning_run_fails_when_llm_unavailable`

`tests/integration/test_tenant_llm_config_flow.py`：

1. `test_reasoning_uses_tenant_llm_route_metadata`
