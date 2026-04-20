# 2 周新手版 AI 个人知识库助手计划（RAG + Agent）

## Summary
- 项目目标锁定为：做一个**单用户、可演示、可写进简历、你能讲清楚原理和实现流程**的 AI 个人知识库助手，而不是做一个复杂产品。
- 最终成品只保留 3 条主线能力：
  - 文档上传与预处理：支持 `pdf`、`md`、`txt`
  - RAG 问答：能基于知识库检索并回答，带引用
  - Agent 能力：优先用 Claude Agent SDK 原生工具，首版只接 `web search`
- 技术栈直接定死，避免你后面反复选型：
  - 后端：FastAPI
  - Agent：Claude Agent SDK
  - 元数据数据库：MySQL
  - 向量数据库：Qdrant
  - Embedding：单独一个 embedding 模型/provider
  - 前端：最小 React 页面，UI 主要交给 AI 生成，你只负责对接接口
- 相比你原来的 `PLAN.md`，明确删除这些内容：
  - 不做 monorepo / packages/shared
  - 不做多知识库管理
  - 不做“对话文件提升到知识库”
  - 不做 GitHub 论文代码检索
  - 不做 OCR
  - 不做多用户、登录、权限
  - 不把“每个对话都能单独传文件”作为 v1 能力

## Key Changes
### 1. 产品范围
- 产品改成“**一个默认知识库 + 聊天问答**”。
- 用户先上传资料到默认知识库，再发起聊天提问。
- 回答必须展示引用来源，至少包含：文件名、页码或段落编号。
- 当知识库检索不到足够信息时，Agent 可以调用原生 `web search` 工具补充，但回答里要区分“知识库内容”和“联网结果”。

### 2. 最小架构
- 不采用你原方案里的多应用拆分，当前仓库直接以后端为主。
- 推荐代码结构只保留 3 个核心层：
  - `app/api`: 路由层，处理上传、聊天、会话、文档列表
  - `app/services`: 文档处理、embedding、检索、agent 调用
  - `app/models`: MySQL 表结构与请求/响应 schema
- 前端放到第二周后半段再接，作为一个最小 React 页面：
  - 文档上传页
  - 聊天页
  - 会话历史侧边栏

### 2.1 项目目录结构（你后面会按这个结构逐步实现）
```text
paper_agent_llm/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ api/
│  │  ├─ __init__.py
│  │  ├─ router.py
│  │  └─ routes/
│  │     ├─ __init__.py
│  │     ├─ health.py
│  │     ├─ documents.py
│  │     └─ chat.py
│  ├─ core/
│  │  ├─ __init__.py
│  │  ├─ config.py
│  │  └─ database.py
│  ├─ models/
│  │  ├─ __init__.py
│  │  ├─ document.py
│  │  ├─ chat.py
│  │  └─ schemas.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ file_service.py
│  │  ├─ parser_service.py
│  │  ├─ chunk_service.py
│  │  ├─ embedding_service.py
│  │  ├─ vector_service.py
│  │  ├─ retrieval_service.py
│  │  ├─ citation_service.py
│  │  └─ agent_service.py
│  └─ utils/
│     ├─ __init__.py
│     └─ text.py
├─ web/
│  ├─ src/
│  │  ├─ App.jsx
│  │  ├─ main.jsx
│  │  ├─ api.js
│  │  ├─ pages/
│  │  │  ├─ ChatPage.jsx
│  │  │  └─ UploadPage.jsx
│  │  └─ components/
│  │     ├─ Sidebar.jsx
│  │     ├─ ChatWindow.jsx
│  │     ├─ MessageList.jsx
│  │     ├─ Composer.jsx
│  │     ├─ UploadPanel.jsx
│  │     └─ CitationList.jsx
├─ tests/
│  ├─ test_health.py
│  ├─ test_documents.py
│  └─ test_chat.py
├─ .env.example
├─ requirements.txt
├─ PLAN.md
└─ README.md
```

### 2.2 每个目录和文件是干嘛的
- `app/`: 后端主目录，FastAPI 服务代码都放这里。
- `app/main.py`: 后端入口文件，负责创建 FastAPI 应用、挂载路由、配置中间件。
- `app/api/`: 接口层，负责接收前端请求并返回 JSON。
- `app/api/router.py`: 统一注册所有路由，避免 `main.py` 变得太乱。
- `app/api/routes/health.py`: 健康检查接口，先用它验证服务能不能正常启动。
- `app/api/routes/documents.py`: 文档上传、文档列表、文档状态查询接口。
- `app/api/routes/chat.py`: 创建会话、发送消息、读取会话历史接口。
- `app/core/`: 基础设施层，放配置、数据库连接这些全局能力。
- `app/core/config.py`: 读取 `.env` 配置，比如数据库地址、Qdrant 配置、模型配置。
- `app/core/database.py`: 创建 MySQL 数据库连接、SQLAlchemy 会话工厂。
- `app/models/`: 数据模型层，描述数据库表和接口输入输出结构。
- `app/models/document.py`: `documents` 和 `document_chunks` 表结构。
- `app/models/chat.py`: `chat_sessions` 和 `chat_messages` 表结构。
- `app/models/schemas.py`: API 的请求体和响应体，比如上传响应、聊天响应、引用结构。
- `app/services/`: 业务逻辑层，真正做文档处理、检索、问答。
- `app/services/file_service.py`: 保存上传文件、生成文件路径、校验文件类型和大小。
- `app/services/parser_service.py`: 解析 PDF、MD、TXT，抽出文本和页码信息。
- `app/services/chunk_service.py`: 把长文本切成多个 chunks，供 embedding 和检索使用。
- `app/services/embedding_service.py`: 调用 embedding 模型，把文本转成向量。
- `app/services/vector_service.py`: 和 Qdrant 交互，负责写入向量和相似度检索。
- `app/services/retrieval_service.py`: 整合“查询 embedding + Qdrant 检索 + 返回候选片段”。
- `app/services/citation_service.py`: 把检索结果整理成引用格式，比如文件名、页码、片段编号。
- `app/services/agent_service.py`: 调用 Claude Agent SDK，把问题和上下文交给模型生成答案。
- `app/utils/`: 放小工具函数，避免把零散逻辑塞进业务文件。
- `app/utils/text.py`: 文本清洗、截断、格式化等通用函数。
- `web/`: 前端目录，第二周再实现，先知道它在整个项目里的位置即可。
- `web/src/App.jsx`: 前端根组件。
- `web/src/main.jsx`: React 启动入口。
- `web/src/api.js`: 前端请求后端接口的统一封装。
- `web/src/pages/ChatPage.jsx`: 聊天主页面。
- `web/src/pages/UploadPage.jsx`: 文档上传页面。
- `web/src/components/Sidebar.jsx`: 左侧会话列表。
- `web/src/components/ChatWindow.jsx`: 聊天区域容器。
- `web/src/components/MessageList.jsx`: 展示消息列表。
- `web/src/components/Composer.jsx`: 输入框和发送按钮。
- `web/src/components/UploadPanel.jsx`: 上传文档的面板。
- `web/src/components/CitationList.jsx`: 展示引用来源。
- `tests/`: 测试目录，后续每做完一个模块就补对应测试。
- `tests/test_health.py`: 测试健康检查接口。
- `tests/test_documents.py`: 测试文档上传和列表接口。
- `tests/test_chat.py`: 测试聊天接口和引用返回。
- `.env.example`: 环境变量模板，告诉你项目需要哪些配置。
- `requirements.txt`: Python 依赖列表。
- `PLAN.md`: 当前项目开发计划和学习路线。
- `README.md`: 项目说明文档，最后用于演示和写简历素材。

### 2.3 你可以把它理解成 3 条主线
- 第一条线是 `api`：负责“接请求、回结果”。
- 第二条线是 `services`：负责“真正干活”，比如解析文档、做检索、调模型。
- 第三条线是 `models + core`：负责“数据和基础设施”，比如表结构、数据库连接、配置读取。

### 2.4 一次请求是怎么走完整个项目的
1. 前端调用 `app/api/routes/chat.py` 的聊天接口。
2. 路由层把问题交给 `retrieval_service.py` 先去检索相关文档片段。
3. 检索结果交给 `citation_service.py` 组装引用信息。
4. 再把“用户问题 + 检索上下文 + 引用编号”交给 `agent_service.py`。
5. `agent_service.py` 调 Claude Agent SDK 返回答案。
6. 最后路由层把 `answer + citations` 返回给前端展示。

### 3. 数据与接口
- 核心表只保留：
  - `documents`: 文件元数据、状态、路径、类型
  - `document_chunks`: chunk 元信息，不存向量，只存与 Qdrant 对应的索引信息
  - `chat_sessions`: 会话
  - `chat_messages`: 消息与引用 JSON
- Qdrant 中只存：
  - `chunk_id`
  - `embedding`
  - `document_id`
  - `page`
  - `text`
- 对外接口固定为：
  - `POST /api/documents/upload`: 上传文档并触发解析、切块、向量化
  - `GET /api/documents`: 文档列表与处理状态
  - `POST /api/chat/sessions`: 新建会话
  - `GET /api/chat/sessions`: 获取会话列表
  - `GET /api/chat/sessions/{id}`: 获取会话与消息
  - `POST /api/chat/sessions/{id}/messages`: 发送问题，返回回答与引用
- 首版响应直接做**非流式**，不要一开始就上 SSE；等核心流程跑通后再考虑流式增强。

### 4. RAG 与 Agent 流程
- 文档处理流程固定为：
  - 文件保存到本地目录
  - PDF/MD/TXT 提取文本
  - 按固定长度切块
  - 调用 embedding 模型生成向量
  - 向量写入 Qdrant，元数据写入 MySQL
- 问答流程固定为：
  - 用户提问
  - 去 Qdrant 检索 Top K chunks
  - 后端把检索结果编号成引用 `[1][2][3]`
  - 将问题 + 检索上下文交给 Claude Agent SDK
  - 若本地检索不足，再允许 agent 调 `web search`
  - 返回 `answer + citations + used_web_search`
- 引用不要完全相信模型自由生成，**引用列表由后端基于检索结果组装**，模型只负责在正文里尽量引用编号。

### 5. 新手教学方式
- 后续实现按“**一个模块一轮**”推进，每轮只做一个明确目标。
- 每轮默认输出格式固定为：
  - 先讲这个模块解决什么问题
  - 再给你要创建/修改的文件
  - 然后给你可直接照着敲的代码
  - 最后给你验证步骤和你在简历/面试里该怎么讲
- 你自己动手敲代码；如果你卡住，我再给你对照版或帮你定位报错。

## 2-Week Schedule
### Week 1：先把 RAG 主链路跑通
1. 第 1 天：项目初始化  
   完成 FastAPI 骨架、环境变量、目录结构、健康检查接口。  
   验证：服务能启动，`/health` 可访问。

2. 第 2 天：MySQL 数据模型  
   建 `documents`、`chat_sessions`、`chat_messages`、`document_chunks`。  
   验证：能插入和查询一条测试数据。

3. 第 3 天：文件上传与保存  
   实现 `pdf/md/txt` 上传、本地存储、状态字段。  
   验证：文件能上传，数据库里能看到状态变化。

4. 第 4 天：文本解析与切块  
   解析 PDF 文本并保留页码，MD/TXT 按纯文本处理。  
   验证：能打印或保存 chunk 结果，页码/段号正确。

5. 第 5 天：Embedding + Qdrant 入库  
   把 chunk 向量写入 Qdrant，并记录对应关系。  
   验证：上传一篇文档后，Qdrant 中能查到向量点。

6. 第 6 天：检索与引用组装  
   完成相似度检索、Top K 返回、引用编号。  
   验证：给一个已知问题，能返回正确片段和来源。

7. 第 7 天：RAG 问答打通  
   用 Claude Agent SDK 接入模型，先不加 web search。  
   验证：问知识库问题时，回答能附带 citations。

### Week 2：补齐 Agent、前端演示和项目包装
1. 第 8 天：会话与消息历史  
   保存用户问题、助手回答、引用 JSON。  
   验证：刷新后还能读到历史会话。

2. 第 9 天：接入 Agent 原生 `web search`  
   当本地召回不足时允许联网搜索。  
   验证：知识库没有答案的问题可以走联网补充。

3. 第 10 天：最小 React 页面  
   用 AI 生成页面骨架，你来接上传、列表、聊天接口。  
   验证：页面能上传文件、发消息、显示回答。

4. 第 11 天：引用展示与错误处理  
   在前端展示文件名、页码、片段摘要；补齐常见错误提示。  
   验证：上传失败、无检索结果、模型报错都有可理解反馈。

5. 第 12 天：端到端联调  
   从“上传文档”到“提问回答”全流程自测。  
   验证：录一遍演示流程，找出卡点并修正。

6. 第 13 天：项目文档与简历话术  
   补 README、项目亮点、架构图、简历描述、面试问答。  
   验证：你能 3 分钟讲清技术选型与主流程。

7. 第 14 天：查漏补缺  
   只修影响演示和理解的问题，不扩功能。  
   验证：项目可稳定演示，核心模块你能独立解释。

## Test Plan
- 上传 `pdf/md/txt` 能成功保存并进入处理流程。
- PDF 能保留页码；MD/TXT 能正确切块。
- 向量成功写入 Qdrant，检索结果与问题相关。
- 问知识库中明确存在的问题时，回答带正确引用。
- 问知识库中不存在的问题时，可触发 `web search` 补充。
- 会话和消息能持久化到 MySQL。
- 前端至少能完成：上传文档、查看文档列表、发起会话、查看回答和引用。

## Assumptions
- 默认环境采用：**本地 MySQL + Qdrant Cloud**。这样既保留 `MySQL + 向量数据库` 经验，又避免没有 Docker 时本地双数据库环境过重。
- v1 不做流式响应；如果前 10 天进度顺利，再把流式作为加分项。
- v1 只有一个默认知识库，不做多知识库切换。
- v1 只支持文本型 PDF，不支持扫描件 OCR。
- Agent 首版只使用 Claude Agent SDK 原生 `web search` 工具；其他复杂 tool 暂不引入。
- 前端以“能演示、能对接”为标准，不把 UI 精修作为主要学习目标。
- 后续我们按模块教学，你每次只实现一个模块，我负责把每个模块拆成新手可执行的步骤和代码骨架。
