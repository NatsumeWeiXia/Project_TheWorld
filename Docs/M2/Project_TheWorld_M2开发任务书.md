# Project_TheWorld M2开发任务书

## 1. 文档目标
基于以下文档形成 M2 可执行开发任务清单，并确保与现有 M1 代码基线兼容：
- `Docs/Project_TheWorld_需求清单.md`
- `Docs/Project_TheWorld_概要设计文档.md`
- `README.md`
- `Docs/Project_TheWorld_环境配置.md`
- `Docs/Project_TheWorld_技术选型.md`
- `Docs/M1/Project_TheWorld_M1详细设计文档.md`
- `Docs/M2/Project_TheWorld_M2详细设计文档.md`

## 2. M2范围与边界
### 2.1 In Scope
1. 推理主链路（单会话串行）：意图识别 -> 属性匹配 -> 本体定位 -> 能力选择 -> 执行 -> 输出。
2. 澄清与恢复：无匹配、多匹配、参数失败重试。
3. 会话/上下文/Trace 落库与查询接口。
4. Graph 页面集成人机对话框（右侧，可收起/展开）。
5. LLM Provider 统一抽象，支持 Deepseek/Qwen 切换。
6. Console 页 GlobalConfig 支持“按 tenant 配置不同 LLM API Key/模型参数”。

### 2.2 Out of Scope
1. 多子会话并行与递归执行（M3）。
2. 完整数据虚拟化（接口本体全模式，M3）。
3. 高级可观测平台对接（Langfuse/LangSmith 全量集成，M3）。

## 3. 关键约束落实
1. Graph 人机对话框必须位于页面右侧，支持 `Collapse/Expand`，默认展开。
2. Deepseek 与 Qwen 必须统一通过同一 Provider 接口接入；`环境配置文档`中的示例代码仅作示例，不作为实现强约束。
3. Console `GlobalConfig` 必须支持同一系统内多 tenant 的 LLM 差异化配置（至少包含 provider、model、api_key、base_url、timeout、thinking 开关等）。

## 4. 总体交付物
1. 后端代码：`reasoning/context/trace/llm_provider` 模块与 API。
2. 前端代码：`m1_console.html` GlobalConfig 增强、`graph_workspace.html` 右侧对话框。
3. 数据库迁移：M2 新增会话/任务/trace/tenant_llm_config 表。
4. 测试：单元 + 集成 + 页面关键交互测试。
5. 文档：API 文档、配置说明、运维手册补充。

## 5. 任务分解（WBS）

### A. 后端推理主链路
1. `M2-A1` 新增 `reasoning` API 与 Schema。
- 文件：`src/app/api/v1/reasoning.py`、`src/app/schemas/reasoning.py`
- 接口：
  - `POST /api/v1/reasoning/sessions`
  - `GET /api/v1/reasoning/sessions/{session_id}`
  - `POST /api/v1/reasoning/sessions/{session_id}/run`
  - `POST /api/v1/reasoning/sessions/{session_id}/clarify`
  - `GET /api/v1/reasoning/sessions/{session_id}/trace`
  - `POST /api/v1/reasoning/sessions/{session_id}/cancel`
- 验收：OpenAPI 可见；错误码与统一响应格式一致。

2. `M2-A2` 实现推理编排服务。
- 文件：`src/app/services/reasoning_service.py`
- 要点：复用 `mcp_metadata_service` + `knowledge_service` + `ontology_service`；实现串行 plan-execute。
- 验收：输入到输出形成闭环，可返回结构化执行步骤。

3. `M2-A3` 实现澄清与恢复策略。
- 规则：
  - 无候选能力 -> 澄清。
  - Top1/Top2 分差低于阈值 -> 澄清。
  - 工具调用失败 -> 最多 2 次重试 + 候选切换。
- 验收：错误可追踪；恢复成功时状态正确流转。

### B. 上下文与链路追踪
1. `M2-B1` 上下文服务。
- 文件：`src/app/services/context_service.py`
- 作用域：`global/session/local/artifact`。
- 验收：跨轮次仅 `session/artifact` 可读回。

2. `M2-B2` Trace 服务。
- 文件：`src/app/services/trace_service.py`
- 事件：`intent_parsed/attributes_matched/ontologies_located/task_planned/task_executed/clarification_asked/recovery_triggered/session_completed/session_failed`。
- 验收：`/trace` 接口可按时间顺序回放。

### C. LLM 统一接入与 Provider 切换（Deepseek/Qwen）
1. `M2-C1` 定义跨 LLM 通用 Provider 接口。
- 文件：`src/app/services/llm/provider_base.py`
- 抽象：`chat_completion(messages, model, stream, tools, response_format, timeout, extra_options)`。
- 验收：业务层不感知 Deepseek/Qwen SDK 差异。

2. `M2-C2` 实现 Deepseek Provider 与 Qwen Provider。
- 文件：
  - `src/app/services/llm/providers/deepseek_provider.py`
  - `src/app/services/llm/providers/qwen_provider.py`
- 约束：统一使用 OpenAI-Compatible 客户端协议，provider 差异封装在 adapter 内。
- 验收：同一输入可由两 Provider 成功调用并返回统一结构。

3. `M2-C3` Provider Factory + Failover（可配置）。
- 文件：`src/app/services/llm/provider_factory.py`
- 验收：按 tenant 配置选择 provider；可禁用/启用 fallback。

### D. 多租户 LLM 配置（Console GlobalConfig）
1. `M2-D1` 新增 tenant LLM 配置数据模型与迁移。
- 表建议：`tenant_llm_config`
- 字段：`tenant_id/provider/model/api_key_cipher/base_url/timeout_ms/enable_thinking/extra_json/status/updated_by/updated_at`
- 验收：支持增改查；API Key 加密存储，不明文落库。

2. `M2-D2` 新增管理接口。
- 路由建议：`/api/v1/config/tenant-llm`
- 能力：按 tenant 查询、保存、校验连通性（可选 `:verify`）。
- 验收：不同 tenant 读取到不同生效配置。

3. `M2-D3` Console GlobalConfig UI 改造。
- 文件：`src/app/ui/m1_console.html`
- 要点：
  - 增加 tenant 下拉。
  - 增加 provider 切换（Deepseek/Qwen）。
  - 增加模型、base_url、api_key、timeout、thinking 等配置项。
- 验收：切换 tenant 后表单自动加载对应配置并可保存。

### E. Graph 右侧对话框（可收起/展开）
1. `M2-E1` Graph 页面布局扩展。
- 文件：`src/app/ui/graph_workspace.html`
- 要点：
  - 右侧 `AI Chat Panel`，默认宽度 360px。
  - 提供 `Collapse/Expand` 按钮；收起后保留浮动展开入口。
  - 移动端（<1024px）降级为抽屉层。
- 验收：不遮挡核心画布操作；状态可记忆（localStorage）。

2. `M2-E2` 图谱上下文对话联动。
- 功能：
  - 将当前选中节点/子图摘要作为可选上下文发送。
  - 支持“发送到对话”快捷动作。
- 验收：对话请求包含可追踪 `session_id` 与 `graph_context`。

### F. 数据查询/分组分析能力补齐（M2 最小版）
1. `M2-F1` 新增 MCP 数据接口（优先物理表本体）。
- `POST /api/v1/mcp/data/query`
- `POST /api/v1/mcp/data/group-analysis`
- 验收：至少支持 `eq/like/in` 过滤、分页、group by + count/sum。

2. `M2-F2` 与推理链路打通。
- 验收：推理任务可自动调用上述接口并写入 trace。

### G. 测试与质量门禁
1. `M2-G1` 单元测试。
- 覆盖：计划生成、澄清判定、恢复策略、provider factory、tenant 配置读写。

2. `M2-G2` 集成测试。
- 覆盖：
  - Deepseek/Qwen 切换。
  - tenant A/B 配置隔离。
  - Graph 右侧对话框 -> 推理 run -> trace 查询闭环。

3. `M2-G3` 前端关键交互测试。
- 覆盖：GlobalConfig 表单行为、Graph 聊天框收起/展开状态保持。

## 6. 迭代排期建议（4 Sprint）
1. Sprint 1：A+B（主链路骨架 + 会话上下文 + trace 表）
2. Sprint 2：C+D（LLM Provider 抽象 + tenant LLM 配置）
3. Sprint 3：E+F（Graph 右侧对话框 + 数据查询/分组分析）
4. Sprint 4：G（联调、回归、文档与发布）

## 7. 验收标准（DoD）
1. 功能验收：
- 推理主链路可稳定执行，支持澄清与恢复。
- Graph 页右侧对话框可收起/展开并可发起会话。
- Deepseek/Qwen 可按 tenant 配置切换。
- Console GlobalConfig 可维护 tenant 级 API Key 与模型参数。

2. 质量验收：
- 单元/集成测试通过；新增核心路径覆盖率不低于 80%。
- 不引入 P0/P1 安全问题（API Key 明文、越权读写）。

3. 文档验收：
- API、配置项、运维说明与实现一致。
- README 与 M2 详细设计有对应更新记录。

## 8. 风险与缓解
1. 风险：多 Provider 返回结构不一致。
- 缓解：统一 Response DTO，provider 适配层兜底归一。

2. 风险：tenant 级密钥管理存在泄露风险。
- 缓解：服务端加密存储 + 前端脱敏展示 + 审计日志。

3. 风险：Graph 对话框影响画布性能与体验。
- 缓解：右栏组件懒加载；收起后停止高频渲染。

## 9. 发布检查清单
1. Alembic 迁移已执行并可回滚。
2. `.env` / `TW_` 配置项补充完成。
3. API 文档与权限头（tenant）验证通过。
4. Graph 与 Console 页面在桌面/移动端均可用。
5. Deepseek/Qwen 连通性 smoke test 通过。
