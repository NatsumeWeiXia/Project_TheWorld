# Project_TheWorld

本文件用于帮助后续开发者（人或大模型）快速理解工程结构、定位改动入口，避免每次需求变更都做全项目扫描。

## 1. 项目概览

- 技术栈：`FastAPI` + `SQLAlchemy` + `Pydantic v2` + `Uvicorn`
- 主要能力：
1. 本体管理（Ontology / Data Attribute / Object Property / Capability）
2. 知识模板管理（class/attribute/relation/capability/fewshot）
3. MCP 元数据检索能力（属性匹配、本体检索、执行详情）
4. 管理控制台页面（`/theworld/v1/console`）
5. 知识图谱分析工作空间（`/theworld/v1/console/graph`）+ MCP Graph Tool 查询
- 当前入口：
1. API 文档：`/docs`
2. 控制台：`/theworld/v1/console`
3. 图谱工作空间：`/theworld/v1/console/graph`

## 2. 运行与测试

### 2.1 依赖安装

```bash
pip install -r requirements.txt
```

### 2.2 启动服务

- Windows：`start_system.bat`
- Linux/macOS：`start_system.sh`
- 停止服务：`stop_system.bat` / `stop_system.sh`

说明：
- 可通过环境变量覆盖配置（前缀 `TW_`），例如 `TW_DATABASE_URL`。
- `start_system.bat` 支持 `TW_USE_LOCAL_SQLITE=1` 快速切本地 SQLite。

### 2.3 测试

```bash
pytest -q
```

测试默认在 `tests/conftest.py` 中强制切换到 `.runtime` 下隔离 SQLite，避免污染共享库。

### 2.4 数据库迁移（Alembic）

已接入 Alembic，配置文件为 `alembic.ini`，迁移目录为 `alembic/versions`。

常用命令：

```bash
alembic upgrade head
alembic downgrade -1
alembic current
```

说明：
1. Alembic 使用运行时配置中的数据库地址（`TW_DATABASE_URL` / `.env` / `settings.database_url`）。
2. 当前已提供 M1 baseline 迁移：`20260218_0001`。

## 3. 系统分层与调用链

一次典型请求的路径：

1. `src/app/api/v1/*.py` 路由层接收请求、参数校验（Pydantic Schema）
2. `src/app/services/*.py` 业务编排与规则校验
3. `src/app/repositories/*.py` 数据访问（SQLAlchemy）
4. `src/app/infra/db/models.py` ORM 模型映射数据库表
5. `src/app/core/response.py` 统一响应包装

配套：
- `src/app/domain/retrieval/*`：检索与评分算法
- `src/app/ui/m1_console.html`：前端管理台（单文件 Vue 页面）

## 4. 关键领域对象

- `OntologyClass`：本体类
- `OntologyDataAttribute`：数据属性（已支持 `array`）
- `OntologyRelation`：对象属性（domain/range）
- `OntologyCapability`：能力（支持 domain 分组触发条件）
- 知识模板：`KnowledgeClass / KnowledgeAttribute / KnowledgeRelationTemplate / KnowledgeCapabilityTemplate / KnowledgeFewshotExample`

## 5. 改需求时的“快速定位索引”

### 5.1 需要改 API 入参/返回字段

1. Schema：`src/app/schemas/ontology.py`、`src/app/schemas/knowledge.py`、`src/app/schemas/mcp_metadata.py`
2. 路由返回结构：`src/app/api/v1/ontology.py`、`src/app/api/v1/knowledge.py`、`src/app/api/v1/mcp_metadata.py`
3. 业务转换规则：`src/app/services/ontology_service.py`、`src/app/services/mcp_metadata_service.py`

### 5.2 需要改数据库结构/映射

1. ORM 模型：`src/app/infra/db/models.py`
2. 启动兼容迁移（运行时补列逻辑）：`src/app/main.py` 中 `_ensure_runtime_schema`

### 5.3 需要改控制台交互

1. 页面与脚本：`src/app/ui/m1_console.html`
2. 该文件包含：
   - 左侧导航/列表
   - 右侧详情编辑
   - 弹窗（属性选择、本体树选择、详情预览等）
   - `Ctrl+S` 快捷保存

### 5.4 需要改检索排序/召回逻辑

1. `src/app/domain/retrieval/hybrid_engine.py`
2. `src/app/domain/retrieval/scorer.py`
3. `src/app/domain/retrieval/query_preprocessor.py`

### 5.5 需要补测试

1. 集成流程：`tests/integration/*`
2. 单元规则：`tests/unit/*`
3. 测试数据库夹具：`tests/conftest.py`

## 6. 项目目录（高价值目录）

```text
Project_TheWorld/
  configs/          # 多环境配置样例
  Docs/             # 需求、架构、数据库、API 设计文档（M1~M4）
  src/app/          # 应用主代码
  tests/            # 自动化测试
  start_system.*    # 启动脚本
  stop_system.*     # 停止脚本
```

## 7. 逐文件说明（按目录）

说明：`__init__.py` 仅用于包声明，业务逻辑很少。

### 7.1 根目录

- `README.md`：当前工程总览与索引（本文件）
- `requirements.txt`：Python 依赖
- `start_system.bat`：Windows 启动脚本（含 PID/日志管理）
- `start_system.sh`：Unix 启动脚本（后台启动 uvicorn）
- `stop_system.bat`：Windows 停止脚本
- `stop_system.sh`：Unix 停止脚本
- `test_m1.db`：本地 SQLite 示例数据库文件（开发/测试可用）
- `.gitattributes`：Git 属性配置

### 7.2 configs

- `configs/dev.yaml`：开发环境配置样例
- `configs/test.yaml`：测试环境配置样例
- `configs/prod.yaml`：生产环境配置样例

### 7.3 Docs

- `Docs/Project_TheWorld_需求清单.md`：总体需求列表
- `Docs/Project_TheWorld_概要设计文档.md`：总体概要设计
- `Docs/Project_TheWorld_环境配置.md`：环境部署说明
- `Docs/本体推理框架技能需求.md`：本体推理与技能需求
- `Docs/M1/Project_TheWorld_M1详细设计文档.md`：M1 详细设计
- `Docs/M2/Project_TheWorld_M2详细设计文档.md`：M2 详细设计
- `Docs/M3/Project_TheWorld_M3详细设计文档.md`：M3 详细设计
- `Docs/M4/Project_TheWorld_M4详细设计文档.md`：M4 详细设计

### 7.4 src

- `src/__init__.py`：包标记

#### src/app

- `src/app/main.py`：FastAPI 应用入口、异常处理、中间件、路由挂载、启动建表/兼容迁移、控制台页面入口
- `src/app/__init__.py`：包标记

#### src/app/api

- `src/app/api/deps.py`：请求依赖（租户头、鉴权头）
- `src/app/api/__init__.py`：包标记
- `src/app/api/v1/__init__.py`：v1 路由包标记
- `src/app/api/v1/ontology.py`：本体域 CRUD、绑定、树、OWL 校验/导出、表映射等接口
- `src/app/api/v1/knowledge.py`：知识模板与 fewshot 接口
- `src/app/api/v1/mcp_metadata.py`：MCP 元数据检索与执行详情接口
- `src/app/api/v1/mcp_graph.py`：MCP Graph Tool 列表与调用接口（供页面与 LLM Tool 复用）

#### src/app/core

- `src/app/core/config.py`：全局配置模型（读取 `TW_` 环境变量）
- `src/app/core/errors.py`：业务异常与错误码定义
- `src/app/core/response.py`：统一响应包装
- `src/app/core/__init__.py`：包标记

#### src/app/domain/retrieval

- `src/app/domain/retrieval/hybrid_engine.py`：混合检索引擎（稀疏+稠密）
- `src/app/domain/retrieval/query_preprocessor.py`：查询预处理
- `src/app/domain/retrieval/scorer.py`：余弦/稀疏/融合评分函数
- `src/app/domain/retrieval/__init__.py`：包标记

#### src/app/infra/db

- `src/app/infra/db/base.py`：SQLAlchemy Declarative Base
- `src/app/infra/db/session.py`：数据库引擎与会话工厂
- `src/app/infra/db/models.py`：全部 ORM 模型定义（ontology + knowledge）
- `src/app/infra/db/__init__.py`：包标记

#### src/app/repositories

- `src/app/repositories/ontology_repo.py`：本体域数据访问层（class/attr/relation/capability/绑定/导出任务等）
- `src/app/repositories/knowledge_repo.py`：知识模板与 fewshot 数据访问层
- `src/app/repositories/__init__.py`：包标记

#### src/app/schemas

- `src/app/schemas/ontology.py`：本体相关请求 schema
- `src/app/schemas/knowledge.py`：知识模板相关请求 schema
- `src/app/schemas/mcp_metadata.py`：MCP 元数据请求 schema
- `src/app/schemas/mcp_graph.py`：MCP Graph Tool 调用请求 schema
- `src/app/schemas/__init__.py`：包标记

#### src/app/services

- `src/app/services/ontology_service.py`：本体核心业务逻辑（继承、绑定、domain/range、capability domain groups、导出等）
- `src/app/services/knowledge_service.py`：知识模板业务逻辑
- `src/app/services/mcp_metadata_service.py`：元数据检索与详情聚合逻辑
- `src/app/services/mcp_graph_service.py`：图谱查询聚合与 MCP Tool 适配（基本信息/详情/关联/继承标记）
- `src/app/services/embedding_service.py`：Embedding 生成（当前为轻量实现）
- `src/app/services/__init__.py`：包标记

#### src/app/ui

- `src/app/ui/m1_console.html`：M1 管理台单页应用（Vue3 + DaisyUI + Tailwind）
- `src/app/ui/graph_workspace.html`：知识图谱分析工作空间页面（Vue3 + Cytoscape）

### 7.5 tests

- `tests/conftest.py`：测试夹具（隔离 SQLite、建表/清表、通用 headers/client）
- `tests/__init__.py`：包标记

#### tests/integration

- `tests/integration/test_m1_console_and_management_flow.py`：控制台可访问性与管理基础流程
- `tests/integration/test_attribute_match_flow.py`：属性匹配流程
- `tests/integration/test_fewshot_retrieval_flow.py`：fewshot 检索流程
- `tests/integration/test_ontology_detail_flow.py`：本体详情聚合与资源更新流程
- `tests/integration/test_ontology_delete_flow.py`：删除资源联动流程
- `tests/integration/test_ontology_owl_alignment_flow.py`：OWL 相关接口流程
- `tests/integration/__init__.py`：包标记

#### tests/unit

- `tests/unit/test_hybrid_scoring.py`：融合评分逻辑单元测试
- `tests/unit/test_inheritance_rules.py`：继承环检测单元测试
- `tests/unit/test_schema_validation.py`：输入 schema 校验测试
- `tests/unit/__init__.py`：包标记

## 8. 主要 API 分组（便于对接方快速浏览）

### 8.1 Ontology API（`/api/v1/ontology`）

- Classes：创建/列表/详情/更新/删除/树/继承
- Data Attributes：创建/列表/详情/更新/删除/与 class 绑定
- Object Properties：创建/列表/详情/更新/删除（domain/range）
- Capabilities：创建/列表/详情/更新/删除（domain groups）
- Hybrid Search：`GET /api/v1/ontology/hybrid-search`（支持 `w_sparse/w_dense`）
- Embedding Backfill：`POST /api/v1/ontology/embeddings:backfill`（按批次回填 class/relation/capability 的 `search_text/embedding`）
- Class DB Mapping：表绑定、字段映射、自动建实体表、实体数据管理（分页/条件/排序/新增/修改）
- OWL：校验、导出

### 8.2 Knowledge API（`/api/v1/knowledge`）

- class/attribute 知识 upsert 与 latest 查询
- relation/capability 模板创建与 latest 查询
- fewshot 创建、列表、向量检索

### 8.3 MCP Metadata API（`/api/v1/mcp/metadata`）

- 属性匹配：`attributes:match`
- 按属性找本体：`ontologies:by-attributes`
- 本体详情聚合：`ontologies/{class_id}`
- 执行详情：`execution/{resource_type}/{resource_id}`

### 8.4 MCP Graph API（`/api/v1/mcp/graph`）

- Tool 列表：`tools:list`
- Tool 调用：`tools:call`
- 当前内置工具（节选）：
  - `graph.list_data_attributes`
  - `graph.list_ontologies`
  - `graph.get_data_attribute_related_ontologies`
  - `graph.get_ontology_related_resources`
  - `graph.get_ontology_details`
  - `graph.get_object_property_details`
  - `graph.get_capability_details`

## 9. 当前已知工程特征

- 已接入 Alembic（含 M1 baseline 迁移 `20260218_0001`），后续结构变更建议通过迁移脚本演进。
- 数据库结构当前仍同时依赖 ORM + 启动期兼容补列逻辑（`main.py` 中 `_ensure_runtime_schema`），建议后续逐步收敛到 Alembic。
- 运行时会在 `startup` 尝试补齐部分兼容字段（例如 capability 的 `domain_groups_json`）。
- 控制台前端是单文件页面，改动集中但容易冲突；建议功能拆分时优先抽组件/模块化脚本。

## 10. 近期修改总结（2026-02）

### 10.1 本体建模与管理台交互

1. Data Attributes 支持 `array` 数据类型（前后端都已打通）
2. 右侧详情页支持 `Ctrl+S` 快捷保存
3. Object Properties 去除 `relation_type` 和 `mcp_bindings_json`，改为 `domain/range` 本体树复选配置
4. Capabilities 去除 `mcp_bindings_json`，新增 `domain_groups` 分组触发（支持 A 或 B+C 形式）
5. Ontologies 的 Associated Entities 可显示 domain/range 关联并标注角色
6. Bound Data Attributes 与 Associated Entities 可点击名称查看详情弹窗并跳转对应可编辑 TAB

关键文件：
- `src/app/schemas/ontology.py`
- `src/app/services/ontology_service.py`
- `src/app/services/mcp_metadata_service.py`
- `src/app/api/v1/ontology.py`
- `src/app/ui/m1_console.html`

### 10.2 自动建实体表（Create Table）

1. 在 Ontologies 的 Physical Table Mapping 中新增 `Create Table` 按钮
2. 按规则在实体库创建表：`t_memento_{ontology_code}`
3. 字段取本体全部 Bound Data Attributes，按 Data Type 映射 PG 类型
4. 创建后自动回填：
   - Physical Table Mapping
   - Bound Data Attributes 下 DB Field Name（field mapping）

新增/关键位置：
- 配置：`src/app/core/config.py`（`entity_database_url` / `entity_database_name`）
- 服务：`src/app/services/ontology_service.py`（`create_entity_table_for_class`）
- 接口：`POST /api/v1/ontology/classes/{class_id}/table-binding:create-table`
- 前端：`src/app/ui/m1_console.html`

### 10.3 实体数据管理（Manage Data）

当本体存在物理表时，显示 `Manage Data` 按钮，弹出实体预览页，支持：
1. 分页展示
2. 条件查询（`eq/like/in`）
3. 排序（字段 + asc/desc）
4. 新增
5. 修改

新增接口：
1. `POST /api/v1/ontology/classes/{class_id}/table-binding:data:query`
2. `POST /api/v1/ontology/classes/{class_id}/table-binding:data`
3. `PUT /api/v1/ontology/classes/{class_id}/table-binding:data/{row_token}`

关键文件：
- `src/app/services/ontology_service.py`
- `src/app/api/v1/ontology.py`
- `src/app/ui/m1_console.html`
- `tests/integration/test_ontology_detail_flow.py`

### 10.4 删除本体外键冲突修复

修复了删除本体时可能出现的 `ontology_inheritance` 外键冲突（`ForeignKeyViolation`）：
1. 删除继承边改为数据库级先删并立即 flush，确保顺序稳定
2. 增加脏数据场景回归测试（租户不一致继承边）

关键文件：
- `src/app/repositories/ontology_repo.py`
- `tests/integration/test_ontology_delete_flow.py`

### 10.5 日志统一时间格式

项目主要日志输出统一为 `YYYY-MM-DD HH:mm:ss`：
1. uvicorn 日志（error/access）
2. 启停脚本输出（bat/sh）
3. 管理台页面日志面板与前端 console 日志

关键文件：
- `configs/uvicorn_log.json`
- `start_system.bat` / `stop_system.bat`
- `start_system.sh` / `stop_system.sh`
- `src/app/ui/m1_console.html`

### 10.6 Graph 工作空间与 MCP Graph Tool（本次会话）

#### 10.6.1 页面与入口

1. 在 `m1_console` 右上角主题切换按钮旁新增 `Graph` 按钮，点击后新 TAB 打开 `/theworld/v1/console/graph`
2. 新增 `/theworld/v1/console/graph` 页面，布局为左侧资源栏 + 右侧图谱画布
3. 资源栏包含 `Data Attributes` 和 `Ontologies` 分类，支持展开/折叠与按 `name/code` 搜索
4. 资源项支持：点击查看详情弹窗、`Add to Graph` 添加节点

#### 10.6.2 图谱交互与规则

1. 节点类型与样式：
   - Ontology：Rectangle（灰色）
   - Data Attribute：Circle（橙色）
   - Object Property：Square（蓝紫色）
   - Capability：Square（淡红色）
2. 画布能力：节点拖拽、缩放、自动布局、节点按 `code` 去重
3. 单击节点查看详情；双击节点执行展开
4. 展开规则：
   - 双击 Data Attribute：展开关联 Ontologies
   - 双击 Ontology：展开关联 Data Attributes / Object Properties / Capabilities，及父/子本体
   - 双击 Object Property：展开 domain/range 并在线上标注
   - 双击 Capability：展开 domain groups 并在线上标注分组名
5. 连线方向：
   - 本体 -> Data Attribute
   - 本体 -> Object Property（domain）
   - Object Property -> 本体（range）
   - 本体 -> Capability
   - 父本体 -> 子本体
6. 连线样式：
   - 继承关系线（父子本体）为灰色虚线
   - `bindingSource=inherited` 产生的资源线为对应颜色虚线
   - 其余关系线为对应颜色实线
7. 自动连线去重：同向关系不重复创建，重复关系会合并 label

#### 10.6.3 MCP Graph Tool 封装与返回字段

1. 新增标准 MCP 风格接口：
   - `POST /api/v1/mcp/graph/tools:list`
   - `POST /api/v1/mcp/graph/tools:call`
2. Object Property 详情返回中 `domain/range` 统一为数组
3. 本体查询返回扩展：
   - `parentOntologies`：仅向上一层父类
   - `childOntologies`：仅向下一层子类
4. 资源聚合保留全继承链：
   - `dataAttributes/objectProperties/capabilities` 仍按全部祖先链继承计算
5. 资源项补充继承标记字段：
   - `bindingSource: self | inherited`
   - `objectProperties.roles: domain | range`

#### 10.6.4 管理台联动增强

1. `m1_console` 的 Ontology 详情页 `Associated Entities` 增强为显示：
   - 本体自身关联项
   - 从父类继承的关联项
2. 关联项标签增加来源标记（`Direct` / `Inherited`）

关键文件：
- `src/app/main.py`
- `src/app/ui/m1_console.html`
- `src/app/ui/graph_workspace.html`
- `src/app/api/v1/mcp_graph.py`
- `src/app/schemas/mcp_graph.py`
- `src/app/services/mcp_graph_service.py`

### 10.7 冗余清理与搜索触发策略（本次会话）

1. 删除未使用代码：
   - 移除 `src/app/services/mcp_graph_service.py` 中未使用的 `_match_query`。
   - 删除未被调用的 `src/app/workers/embedding_worker.py`。
2. 搜索触发策略统一为按钮触发：
   - `/theworld/v1/console` 主搜索框右侧新增 `Search` 按钮，点击后才发起查询。
   - `/theworld/v1/console/graph` 的 `Ontologies/Data Attributes` 搜索框右侧新增 `Search` 按钮，点击后才发起查询。
3. Global Config 增强：
   - 新增“重置默认权重（0.45/0.55）”按钮。
   - 新增“当前生效比例预览”。
   - 新增“离线回填”触发按钮（调用 `POST /api/v1/ontology/embeddings:backfill`）。

### 10.8 搜索质量与结果展示对齐（本次会话）

1. Hybrid Search 过滤条件增强（后端）：
   - 在 `top_n` 与 `score_gap` 之外，新增 `relative_diff` 条件。
   - 三个条件同时生效：`Top-N`、相邻分数断层、以及 `score >= max_score * relative_diff`。
2. 关键词匹配增强（后端）：
   - 在 PostgreSQL 场景接入 `pg_trgm` 的 `similarity(query, search_text)` 作为 sparse 分（可回退到原逻辑）。
   - 需要数据库启用扩展：`CREATE EXTENSION IF NOT EXISTS pg_trgm;`
3. Global Config 策略增强（前端）：
   - 拆分为两组权重：
     - 单词搜索（query token <= 2）：`word_w_sparse/word_w_dense`
     - 语句搜索（query token > 2）：`sentence_w_sparse/sentence_w_dense`
   - 新增 `Top-N`、`Score Gap`、`Relative Difference` 全局配置并持久化到 localStorage。
4. 控制台与图谱搜索结果展示统一：
   - 搜索结果按接口 score 降序展示。
   - Ontologies 在“搜索态”使用列表展示（非树），在“非搜索态”保留树形结构。
   - Console 的 Ontology 树节点支持展开/收起。
5. MCP Graph Tool 返回结构增强：
   - `graph.list_data_attributes` / `graph.list_ontologies` 在 `tools:call` 返回中增加 `query` 字段，返回结构为：
     - `{ "query": "...", "items": [...] }`
