# 本体推理框架技能需求

-----

### 1. 设计模式与技术概念 (Concepts & Patterns)

决定了研发人员是否理解“如何让 AI 思考”以及“如何构建复杂的业务流”。

#### **A. 必须理解 (Must Have)**

- **Agentic Workflow (智能体工作流)**：
  - **ReAct 模式 (Reason + Act)**：核心。对应需求 2.2，即“观察(User Input) -> 思考(Reasoning) -> 行动(Call MCP) -> 观察结果”的循环。
  - **Tool Use / Function Calling (工具调用)**：对应需求 1.2 和 2.1。必须理解如何定义 JSON Schema，如何让 LLM 准确填充参数，以及如何处理调用失败。
  - **Structured Output (结构化输出)**：对应需求 1.2。能够强制 LLM 输出严格的 JSON 格式，而不是自然语言，这是系统稳定性的基石。
- **RAG (检索增强生成) 基础**：
  - **Hybrid Search (混合检索)**：对应需求 2.1。必须理解“关键词检索 (BM25)”与“向量检索 (Dense)”的区别及结合场景（因为纯向量检索无法精确匹配具体的属性 ID）。
- **架构模式**：
  - **FSM (有限状态机)**：对应需求 2.2 和 2.4。推理过程不是线性的，而是状态流转（如：待执行 -> 执行中 -> 需人工确认 -> 完成）。
  - **Async / Event-Driven (异步/事件驱动)**：对应需求 2.4。主会话拉起子会话、并行执行任务，必须基于异步消息或协程机制。

#### **B. 加分项 (Bonus / Advanced)**

- **Advanced RAG (高级 RAG)**：
  - **GraphRAG (基于图谱的 RAG)**：对应需求 1.4 和 2.1。鉴于你们是“本体”驱动，如果候选人懂如何利用知识图谱增强检索（而不仅仅是向量相似度），是极大的加分项。
  - **Re-ranking (重排序)**：检索出 50 个属性后，使用 Cross-Encoder 模型精选 Top 5，能大幅提升 2.2 的准确率。
- **Agent 高级模式**：
  - **Plan-and-Solve (规划与执行)**：对应需求 2.2 中“生成待执行列表”的逻辑。先生成 Plan，再逐个 Execute。
  - **Reflexion (自我反思/自愈)**：对应需求 2.4“会话内错误处理”。当 MCP 报错时，Agent 能自动分析错误日志并修正参数重试，而不需要抛给用户。
  - **Memory Management (记忆管理)**：对应需求 2.5。理解 Short-term Memory (Window) vs Long-term Memory (Vector DB) 的区别，以及 Summary 压缩策略。

------

### 2. 技术框架 (Frameworks & Stack)

决定了研发人员能否高效地将设计落地为代码。

#### **A. 必须掌握 (Must Have)**

- **LLM Orchestration (编排框架)**：
  - **LangChain (Python/JS)** 或 **Semantic Kernel (C#/Java)**：这是目前构建 LLM 应用的“标准库”。必须熟练使用其 `Chains`, `Agents`, `Tools` 模块。
- **Vector Database (向量数据库)**：
  - **Milvus / Pgvector / Chroma / Qdrant** (任一即可)：对应需求 2.1。需要懂基本的 CRUD、索引构建和元数据过滤 (Metadata Filtering)。
- **数据校验与序列化**：
  - **Pydantic (Python)** 或 **Zod (JS)**：这是实现“结构化输出”和“本体参数提取”的神器。不懂这个无法做企业级 Agent。
- **后端基础**：
  - **FastAPI (Python) / Spring Boot (Java)**：支持高并发和异步处理。

#### **B. 加分项 (Bonus / Advanced)**

- **Agent 专用框架 (最契合需求)**：
  - **LangGraph**：这是目前最火的框架，专门用于构建 **“有循环、有状态”** 的多智能体系统。**几乎完美映射2.2 和 2.4 的需求**（状态机、子图 Sub-graph）。
  - **DSPy**：一种通过编程方式优化 Prompt 的框架。如果候选人会这个，说明他对 Prompt 工程有极深的理解，能大幅提升系统的稳定性。
- **可观测性 (Observability)**：
  - **LangSmith / Arize Phoenix**：对应需求 2.6。如果候选人用过这些工具来追踪 Token 消耗和推理链路，说明他有生产环境的实战经验。
- **图数据库**：
  - **Neo4j / NebulaGraph**：如果候选人熟悉图数据库的 Cypher 查询语言，对实现 1.4 本体图和 2.1 的关联查询非常有帮助。

------

### 3. 推荐参考的开源框架 (Open Source References)

建议深入研究以下开源项目，它们的代码结构直接对应了核心需求。

#### **1. LangGraph (最强推荐)**

- **对应需求：** 2.2 (推理引导), 2.4 (会话管理), 2.5 (上下文状态)
- **理由：** LangGraph 的核心概念就是 **"State Machine" (状态机)** 和 **"Cyclic Graph" (循环图)**。
  - 它允许定义 `State`（即上下文）。
  - 它允许定义 `Node`（即本体能力/MCP）。
  - 它允许定义 `Edge`（即推理流转逻辑，比如：如果有子任务 -> 进入子会话节点）。
  - **它天生支持“主图调用子图”的架构，完美解决主会话与子会话的嵌套问题。**

#### **2. LlamaIndex (RAG 首选)**

- **对应需求：** 2.1 (系统 MCP - 数据属性查询)
- **理由：** LlamaIndex 在 **"Data Indexing" (数据索引)** 方面比 LangChain 更强。
  - 它有成熟的 `RouterQueryEngine`，可以根据问题自动选择是查向量索引、还是查关键词索引、还是查 SQL 数据库。这正是你 2.1 中需要的“根据属性匹配查询”的能力。

#### **3. Microsoft AutoGen**

- **对应需求：** 2.4 (多会话管理), 3.1 (领域组合)
- **理由：** AutoGen 擅长 **"Multi-Agent Conversation" (多智能体对话)**。
  - 如果决定在某些复杂节点引入“多智能体协作”，AutoGen 是最佳参考。
  - 它的 `GroupChatManager` 模式可以参考用于设计主会话如何分发任务给子会话。

#### **4. MetaGPT**

- **对应需求：** 1.3 (知识框架 - SOP)
- **理由：** MetaGPT 强调 **"Standard Operating Procedure (SOP)"**。
  - 它将现实世界的岗位（如产品经理、架构师）映射为 Agent。你的需求中提到“本体挂载 Skill”，这其实就是一种 SOP。参考 MetaGPT 如何定义 `Role` 和 `Action`，有助于设计本体的知识结构。