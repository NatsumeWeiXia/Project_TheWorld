# Project_TheWorld

本文件描述当前工程状态，用于开发定位与协作。

## 1. 项目概览

- 技术栈：`FastAPI` + `SQLAlchemy` + `Pydantic v2` + `Uvicorn`
- 编排与模型调用：`LangGraph` + `LangChain`
- 主要入口：
1. API 文档：`/docs`
2. 管理控制台：`/theworld/v1/console`
3. 图谱工作台：`/theworld/v1/console/graph`

## 2. 当前功能状态

### 2.1 Ontology（本体建模）

1. Ontology Class：CRUD、树、继承。
2. Data Attribute：CRUD、与本体绑定，支持 `array` 数据类型。
3. Object Property：CRUD，基于 `domain/range` 建模。
4. Capability：CRUD，基于 `domain_groups` 建模。
5. Hybrid Search：支持 `w_sparse/w_dense`、`top_n`、`score_gap`、`relative_diff`。
6. Embedding Backfill：支持离线回填 class/relation/capability 向量。

### 2.2 Knowledge（知识模板）

1. class/attribute 知识 upsert 与 latest 查询。
2. relation/capability 模板管理。
3. few-shot 示例管理与检索。

### 2.3 MCP 能力

1. Metadata：
   - 属性匹配
   - 按属性找本体
   - 本体详情聚合
   - 资源执行详情
2. Graph Tool：
   - `tools:list`
   - `tools:call`
   - 内置 `graph.list_* / graph.get_*` 查询能力
3. Data：
   - `query`（条件查询）
   - `group-analysis`（分组聚合）

### 2.4 Reasoning（推理会话）

1. 会话接口：`create / run / clarify / trace / cancel / get_session`。
2. 当前主链路：`understand_intent -> discover_candidates -> select_anchor_ontologies -> inspect_ontology -> execute -> finalize`。
3. `inspect_ontology`：
   - 基于 `graph.get_ontology_details` 中 capability/object_property 的 `name/description` 做选择决策。
   - 选定后再获取 `graph.get_capability_details` 或 `graph.get_object_property_details` 作为执行上下文。
4. `execute`：
   - 基于 `CapabilityExecutor` / `ObjectPropertyExecutor` 执行抽象。
   - 由 LLM 规划数据执行参数并调用 `mcp.data.query` / `mcp.data.group-analysis`。
5. 失败策略：
   - LLM 失败不做回退，直接报错并结束当前执行。

### 2.5 Console 与 Graph 页面

1. `m1_console.html`：本体与知识管理、全局配置、实体表与实体数据管理。
2. `graph_workspace.html`：图谱浏览与展开、右侧 Graph Chat、Audit 查看。

### 2.6 可观测与审计

1. 推理链路中的 LLM 调用与 MCP 调用进入 `reasoning_trace_event`。
2. Trace 事件通过 `TraceService` 同步下沉 Langfuse。
3. Graph 页面可通过会话 trace 查看完整链路事件。

## 3. 运行与测试

### 3.1 安装依赖

```bash
pip install -r requirements.txt
```

### 3.2 启动服务

- Windows：`start_system.bat`
- Linux/macOS：`start_system.sh`
- 停止：`stop_system.bat` / `stop_system.sh`

### 3.3 执行测试

```bash
pytest -q
```

测试默认使用 `tests/conftest.py` 中隔离 SQLite（`.runtime`）。

### 3.4 数据库迁移（Alembic）

```bash
alembic upgrade head
alembic downgrade -1
alembic current
```

迁移目录：`alembic/versions`。运行时也包含 `main.py` 中的最小兼容补齐逻辑（`_ensure_runtime_schema`）。

## 4. 代码结构与定位

```text
Project_TheWorld/
  Docs/             # 设计文档（M1~M4）
  configs/          # 环境配置样例
  src/app/
    api/v1/         # HTTP API
    services/       # 业务编排与领域服务
    repositories/   # 数据访问
    infra/db/       # ORM 与数据库连接
    schemas/        # Pydantic 请求模型
    ui/             # console + graph 页面
  tests/
    integration/    # 集成测试
    unit/           # 单元测试
```

常用定位：

1. 推理链路：`src/app/services/reasoning_service.py`
2. 执行器抽象：`src/app/services/reasoning_executors.py`
3. Graph Tool 聚合：`src/app/services/mcp_graph_service.py`
4. MCP Data：`src/app/services/mcp_data_service.py`
5. 审计/可观测：`src/app/services/trace_service.py`、`src/app/services/observability/*`

## 5. API 分组

1. Ontology：`/api/v1/ontology`
2. Knowledge：`/api/v1/knowledge`
3. MCP Metadata：`/api/v1/mcp/metadata`
4. MCP Graph：`/api/v1/mcp/graph`
5. MCP Data：`/api/v1/mcp/data`
6. Reasoning：`/api/v1/reasoning`
7. Config：`/api/v1/config`

## 6. 配置约定

1. 环境变量前缀：`TW_`。
2. 按租户隔离：
   - LLM 配置（`tenant-llm`）
   - 搜索配置（`tenant-search-config`）
3. 激活租户记录：`active-tenants` 用于查看系统内最近活跃租户列表。
4. Langfuse 配置接口：`/api/v1/config/observability/langfuse`。
