# Project_TheWorld M1 详细设计文档（现状对齐版）

## 1. 文档目标

本文档用于描述 **当前代码已实现的 M1 设计与行为**，作为开发、联调、测试和运维的统一基线。

对齐范围：
1. 本体域（Ontology / Data Attribute / Object Property / Capability）建模与管理。
2. 知识模板管理（class/attribute/relation/capability/fewshot）。
3. MCP Metadata 与 MCP Graph Tool 接口。
4. Console 与 Graph 页面行为。
5. Hybrid Search（关键词 + 向量 + 过滤策略）。

---

## 2. M1 已实现范围（In Scope）

1. 本体域完整 CRUD：
   - Classes、Data Attributes、Object Properties、Capabilities。
2. 继承关系管理：
   - 父子本体维护、环检测、删除关联继承边清理。
3. 绑定关系管理：
   - class-attribute 绑定、relation domain/range、capability domain_groups。
4. 本体表映射与实体数据管理：
   - table binding、field mapping、create table、query/create/update data row。
5. OWL 能力：
   - 校验与导出。
6. Hybrid Search：
   - 稀疏 + 稠密融合；
   - top_n、score_gap、relative_diff 三条件联合截断；
   - PostgreSQL 场景支持 pg_trgm 相似度 sparse 分。
7. 知识管理：
   - class/attribute upsert + latest；
   - relation/capability 模板创建 + latest；
   - fewshot 创建/列表/检索。
8. 系统级 MCP Metadata：
   - `attributes:match`、`ontologies:by-attributes`、`ontologies/{class_id}`、`execution/{type}/{id}`。
9. MCP Graph Tool：
   - `tools:list`、`tools:call`；
   - 7 个内置 graph tools。
10. 前端页面：
   - Console：`/theworld/v1/console`
   - Graph：`/theworld/v1/console/graph`

---

## 3. 技术基线（实际实现）

1. Python 3.13.x
2. FastAPI + SQLAlchemy + Pydantic v2 + Uvicorn
3. 数据库：
   - 默认可运行于 SQLite（测试/本地）
   - 部署主场景为 PostgreSQL（含 ontology 库与 entity 库）
4. 检索与向量：
   - Embedding 通过 `EmbeddingService` 调用外部服务
   - Hybrid Search 在应用层融合
   - PostgreSQL 可选 `pg_trgm` 用于 trigram 模糊匹配
5. 前端：
   - 单文件 Vue3 页面（DaisyUI + Tailwind）

说明：
1. 当前仓库已接入 Alembic（含 M1 baseline），但运行时仍保留启动期兼容补列逻辑。

---

## 4. 系统架构与调用链

1. API 层：`src/app/api/v1/*.py`
2. Service 层：`src/app/services/*.py`
3. Repository 层：`src/app/repositories/*.py`
4. ORM 模型：`src/app/infra/db/models.py`
5. 统一响应：`src/app/core/response.py`
6. 检索模块：`src/app/domain/retrieval/*`

---

## 5. 数据模型（实际实现要点）

核心实体：
1. `ontology_class`
2. `ontology_inheritance`
3. `ontology_data_attribute`
4. `ontology_relation`
5. `ontology_capability`
6. 绑定与映射表：
   - `ontology_class_data_attr_ref`
   - `ontology_relation_domain_ref`
   - `ontology_relation_range_ref`
   - `ontology_class_capability_ref`
   - `ontology_class_table_binding`
   - `ontology_class_field_mapping`
7. 导出任务：`ontology_export_task`
8. 知识表：
   - `knowledge_class`
   - `knowledge_attribute`
   - `knowledge_relation_template`
   - `knowledge_capability_template`
   - `knowledge_fewshot_example`

关键字段现状：
1. Data Attribute `data_type` 已支持：`string/int/date/boolean/json/array`
2. Object Property 使用 `domain/range` 绑定，不再依赖旧的 `relation_type/mcp_bindings_json` 作为前端主配置语义
3. Capability 使用 `domain_groups_json` 表达触发域分组
4. 检索字段：
   - `search_text`
   - `embedding`

---

## 6. API 设计（实际接口）

### 6.1 Ontology API（`/api/v1/ontology`）

1. Classes：
   - `POST /classes`
   - `GET /classes`
   - `GET /classes/{class_id}`
   - `PUT /classes/{class_id}`
   - `DELETE /classes/{class_id}`
   - `GET /tree`
   - `POST /classes/{class_id}/inheritance`
2. Data Attributes：
   - `POST /data-attributes`
   - `GET /data-attributes`
   - `GET /data-attributes/{attribute_id}`
   - `PUT /data-attributes/{attribute_id}`
   - `DELETE /data-attributes/{attribute_id}`
   - `POST /classes/{class_id}/data-attributes:bind`
3. Object Properties：
   - `POST /object-properties`
   - `GET /object-properties`
   - `GET /object-properties/{relation_id}`
   - `PUT /object-properties/{relation_id}`
   - `DELETE /object-properties/{relation_id}`
4. Capabilities：
   - `POST /capabilities`
   - `GET /capabilities`
   - `GET /capabilities/{capability_id}`
   - `PUT /capabilities/{capability_id}`
   - `DELETE /capabilities/{capability_id}`
   - `POST /classes/{class_id}/capabilities:bind`
5. Hybrid Search：
   - `GET /hybrid-search`
   - 参数：`q/types/top_k/score_gap/relative_diff/w_sparse/w_dense`
6. Embedding Backfill：
   - `POST /embeddings:backfill`
7. Table Binding / Data：
   - `PUT /classes/{class_id}/table-binding`
   - `PUT /classes/{class_id}/table-binding/field-mapping`
   - `POST /classes/{class_id}/table-binding:create-table`
   - `POST /classes/{class_id}/table-binding:data:query`
   - `POST /classes/{class_id}/table-binding:data`
   - `PUT /classes/{class_id}/table-binding:data/{row_token}`
8. OWL：
   - `POST /owl:validate`
   - `GET /owl:export`

### 6.2 Knowledge API（`/api/v1/knowledge`）

1. Class knowledge：upsert + latest
2. Attribute knowledge：upsert + latest
3. Relation template：create + latest
4. Capability template：create + latest
5. Fewshot：create/list/search

### 6.3 MCP Metadata API（`/api/v1/mcp/metadata`）

1. `POST /attributes:match`
2. `POST /ontologies:by-attributes`
3. `GET /ontologies/{class_id}`
4. `GET /execution/{resource_type}/{resource_id}`

### 6.4 MCP Graph API（`/api/v1/mcp/graph`）

1. `POST /tools:list`
2. `POST /tools:call`
3. 主要 tool：
   - `graph.list_data_attributes`
   - `graph.list_ontologies`
   - `graph.get_data_attribute_related_ontologies`
   - `graph.get_ontology_related_resources`
   - `graph.get_ontology_details`
   - `graph.get_object_property_details`
   - `graph.get_capability_details`

返回结构说明（list tools）：
1. `graph.list_data_attributes` / `graph.list_ontologies` 返回：
   - `{ "query": "...", "items": [...] }`
2. 搜索项含 `score` 字段（无 query 时 `score` 为 `null`）。

---

## 7. Hybrid Search 设计（现状）

流程：
1. query 预处理（lower + trim）
2. dense 分：embedding cosine
3. sparse 分：
   - 默认 token overlap（应用层）
   - PostgreSQL + `pg_trgm` 可用时改用 `similarity(query, search_text)` 覆盖 sparse 分
4. 融合：
   - `hybrid_score = normalized(w_sparse,w_dense)`
5. 截断（同时生效）：
   - `top_n`
   - `score_gap`（相邻分断层）
   - `relative_diff`（`score >= max_score * relative_diff`）

前端权重策略（Global Config）：
1. 单词搜索（query token <= 2）：`word_w_sparse/word_w_dense`
2. 语句搜索（query token > 2）：`sentence_w_sparse/sentence_w_dense`

---

## 8. 前端交互设计（现状）

### 8.1 Console（`m1_console.html`）

1. 资源管理：
   - Ontologies / Data Attributes / Object Properties / Capabilities
2. 编辑与联动：
   - 详情编辑、绑定配置、domain/range、capability domain groups
3. 搜索：
   - 按按钮触发
   - 结果按后端 score 顺序展示
   - Ontologies：
     - 非搜索态：树形（可展开/收起）
     - 搜索态：列表（按 score）
4. Global Config：
   - 两组权重（单词/语句）
   - `Top-N`、`Score Gap`、`Relative Difference`
   - Embedding Backfill 触发

### 8.2 Graph Workspace（`graph_workspace.html`）

1. 左侧资源区：
   - Data Attributes / Ontologies
2. 搜索：
   - 按按钮触发
   - Ontologies：
     - 非搜索态树形
     - 搜索态列表（按 score）
3. 画布能力：
   - 节点添加、双击展开、自动布局、关系去重、继承/来源样式标识

---

## 9. 测试现状

1. 单元测试：
   - 评分融合与过滤逻辑
   - 继承规则、schema 校验
2. 集成测试：
   - console/management 基础流程
   - hybrid search + graph tools
   - ontology 详情、删除、owl、fewshot 等流程

---

## 10. 部署与配置（现状）

1. 启动脚本：
   - `start_system.bat` / `start_system.sh`
2. 关键配置（`TW_` 前缀）：
   - 主数据库连接
   - 实体库连接
   - 其它服务参数
3. PostgreSQL 建议：
   - 启用 `pg_trgm` 以提升关键词模糊匹配：
     - `CREATE EXTENSION IF NOT EXISTS pg_trgm;`

---

## 11. M1 未实现项（文档内保留说明）

以下能力在当前仓库中仍未实现为完整生产方案（不影响本次 M1 验收范围）：

1. 完整 RBAC 体系（当前为基础鉴权依赖 + 租户头隔离）。
2. OpenTelemetry 全链路埋点体系（当前主要是应用日志与 trace_id 返回）。
3. 独立异步 Embedding Worker 进程与队列化索引更新（当前已提供离线 backfill 接口，实时写入在服务内同步处理）。
4. 高规模性能压测基线（如 10 万级属性 P95 指标）未形成文档化验收报告。
5. Alembic 细粒度迁移治理（当前仅有 baseline，且部分兼容补列仍在启动逻辑中）。

---

## 12. 参考文件

1. `README.md`
2. `src/app/api/v1/ontology.py`
3. `src/app/api/v1/knowledge.py`
4. `src/app/api/v1/mcp_metadata.py`
5. `src/app/api/v1/mcp_graph.py`
6. `src/app/services/ontology_service.py`
7. `src/app/services/mcp_graph_service.py`
8. `src/app/ui/m1_console.html`
9. `src/app/ui/graph_workspace.html`
