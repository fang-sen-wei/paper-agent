# Paper Agent LLM

Paper Agent LLM 是一个面向科研阅读场景的文献知识库与智能问答项目。它支持上传论文或文本资料，解析并切分文档内容，写入向量数据库后进行语义检索，并通过 Agent 生成带引用来源的中文回答。

## 功能特性

- 文献管理：上传、查看、删除文档，支持 PDF、TXT、Markdown 文件。
- 文档解析：自动解析文本内容，按配置切分为可检索的 chunks。
- 向量索引：调用 Embedding 服务生成向量，并写入 Qdrant。
- 知识检索：基于问题检索相似文献片段，返回来源、页码/段落和相似度。
- 智能对话：基于已索引文献进行多轮问答，回答中保留引用来源。
- 联网补充：会话可选开启 Tavily 搜索，在知识库不足或需要外部信息时补充回答。
- Web 界面：提供首页、文献管理、知识检索和聊天会话页面。

## 技术栈

- 后端：FastAPI、SQLAlchemy Async、Pydantic Settings、Claude Agent SDK
- 数据库：MySQL 或兼容 MySQL 协议的数据库
- 向量库：Qdrant
- 文档解析：pypdf、文本解析
- Embedding：OpenAI 兼容接口，默认配置为阿里云百炼 DashScope
- 网页搜索：Tavily
- 前端：React、TypeScript、Vite、Tailwind CSS、Lucide React

## 项目结构

```text
paper_agent_llm/
├── app/                    # FastAPI 后端
│   ├── api/                # API 路由
│   ├── core/               # 配置、数据库初始化
│   ├── models/             # SQLAlchemy 模型与接口 schema
│   └── services/           # 文档解析、切块、检索、Agent、向量服务
├── frontend/               # Vite + React 前端
│   ├── public/
│   └── src/
├── requirements.txt        # Python 依赖
├── test.py                 # Agent SDK 调用测试脚本
└── README.md
```

## 环境要求

- Python 3.12 推荐，至少需要支持 Python 3.10+ 语法。
- Node.js 20+ 推荐。
- MySQL 数据库。
- Qdrant 服务，可以使用本地 Qdrant 或 Qdrant Cloud。
- 可用的 Embedding API Key。
- 可用的 Agent 模型 API Key。
- Tavily API Key 仅在开启联网搜索时需要。

## 快速启动

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd paper_agent_llm
```

### 2. 准备后端环境

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

### 3. 准备数据库

先创建一个 MySQL 数据库，例如：

```sql
CREATE DATABASE paper_agent_llm DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

后端启动时会自动创建项目需要的数据表。

### 4. 准备 Qdrant

如果使用本地 Qdrant，可以用 Docker 启动：

```bash
docker run -p 6333:6333 qdrant/qdrant
```

如果使用 Qdrant Cloud，请准备好 `QDRANT_URL` 和 `QDRANT_API_KEY`。

### 5. 配置后端环境变量

在项目根目录创建 `.env` 文件。`.env` 已在 `.gitignore` 中忽略，请不要提交到 GitHub。

```env
APP_NAME=Paper Agent LLM
APP_ENV=development
APP_VERSION=0.1.0
API_PREFIX=/api
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

DATABASE_URL=mysql+aiomysql://root:your_password@127.0.0.1:3306/paper_agent_llm?charset=utf8mb4
DB_ECHO=false

FILE_STORAGE_ROOT=.data/storage
MAX_UPLOAD_FILES=3
MAX_UPLOAD_SIZE_MB=25

CHUNK_SIZE=500
CHUNK_OVERLAP=100

EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_VECTOR_SIZE=256
EMBEDDING_BATCH_SIZE=8
EMBEDDING_TIMEOUT_SECONDS=60

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME=paper_agent_chunks

RETRIEVAL_TOP_K=5
RETRIEVAL_SCORE_THRESHOLD=0.3
RETRIEVAL_CANDIDATE_TOP_K=12
RETRIEVAL_QUERY_EXPANSION_LIMIT=2
RERANK_KEYWORD_WEIGHT=0.15
CITATION_TEXT_PREVIEW_LENGTH=120

ANTHROPIC_BASE_URL=https://api-inference.modelscope.cn
ANTHROPIC_API_KEY=your_agent_api_key
AGENT_MODEL=Qwen/Qwen3.5-397B-A17B
AGENT_MAX_TURNS=8

TAVILY_API=your_tavily_api_key
```

说明：

- `DATABASE_URL` 使用 `mysql+aiomysql://` 前缀。
- `EMBEDDING_API_KEY` 用于生成文档向量。
- `QDRANT_URL` 本地默认是 `http://localhost:6333`。
- `ANTHROPIC_BASE_URL` 和 `ANTHROPIC_API_KEY` 会传给 Claude Agent SDK；当前默认配置指向 ModelScope，可按实际模型服务调整。
- `TAVILY_API` 只在聊天会话开启联网搜索时使用。

### 6. 启动后端

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动成功后可以访问：

- 后端根路径：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

### 7. 启动前端

打开新的终端窗口：

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

```text
http://localhost:5173
```

前端开发服务器已配置 `/api` 代理，默认转发到 `http://127.0.0.1:8000`。如果你要连接其他后端地址，可以在前端环境变量中设置 `VITE_API_BASE`。

## 使用流程

1. 打开 `http://localhost:5173`。
2. 进入“文献管理”，上传 PDF、TXT 或 Markdown 文件。
3. 点击文档旁的解析按钮，系统会解析、切块并自动写入向量索引。
4. 进入“知识检索”，输入问题，查看命中的文献片段和引用来源。
5. 进入“聊天会话”，新建会话后开始提问。
6. 如需限定检索范围，可以在会话中选择某一篇文献。
7. 如需外部信息补充，可以勾选“联网搜索”。

## 常用接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/documents/upload` | 上传文档 |
| `GET` | `/api/documents/list` | 获取文档列表 |
| `POST` | `/api/documents/{document_id}/process` | 解析、切块并索引文档 |
| `GET` | `/api/documents/{document_id}/chunks` | 查看文档切片 |
| `POST` | `/api/documents/{document_id}/index` | 重建文档向量索引 |
| `POST` | `/api/documents/search` | 文献知识库检索 |
| `POST` | `/api/chat/sessions` | 创建聊天会话 |
| `GET` | `/api/chat/sessions` | 获取聊天会话列表 |
| `POST` | `/api/chat/sessions/{session_id}/messages/stream` | 流式聊天问答 |

## 支持的文件与限制

- 支持格式：`.pdf`、`.txt`、`.md`
- 默认单次最多上传：3 个文件
- 默认单文件最大：25 MB
- 上传文件默认保存在：`.data/storage/uploads`

这些限制可以通过 `.env` 中的 `MAX_UPLOAD_FILES`、`MAX_UPLOAD_SIZE_MB` 和 `FILE_STORAGE_ROOT` 调整。

## 开发命令

后端开发：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端开发：

```bash
cd frontend
npm run dev
```

前端构建：

```bash
cd frontend
npm run build
```

前端代码检查：

```bash
cd frontend
npm run lint
```

Agent SDK 简单测试：

```bash
python test.py
```

运行测试脚本前，请确认 `.env` 中的 Agent 模型配置已经填写，并注意该脚本会实际调用模型服务。

## 常见问题

### 后端启动时报数据库连接错误

请确认：

- MySQL 已启动。
- 数据库已创建。
- `.env` 中的 `DATABASE_URL` 用户名、密码、端口和数据库名正确。

### 文档索引时报 Embedding 配置错误

请确认：

- `.env` 中已配置 `EMBEDDING_API_KEY`。
- `EMBEDDING_BASE_URL`、`EMBEDDING_MODEL` 与实际服务匹配。
- `EMBEDDING_VECTOR_SIZE` 与 Qdrant collection 的向量维度一致。

### Qdrant 向量维度不匹配

如果修改过 `EMBEDDING_VECTOR_SIZE` 或 Embedding 模型，旧的 Qdrant collection 可能和新配置不一致。开发环境中可以删除旧 collection 后重新索引文档，或保持模型维度配置不变。

### 前端请求接口失败

请确认：

- 后端运行在 `http://127.0.0.1:8000`。
- 前端运行在 `http://localhost:5173`。
- `frontend/vite.config.ts` 中的 `/api` 代理目标与后端地址一致。

### 联网搜索不可用

请确认 `.env` 中已配置 `TAVILY_API`，并且聊天会话中开启了“联网搜索”。

## 发布到 GitHub 前建议

- 不要提交 `.env`、`.data/`、`.venv/`、`frontend/node_modules/`、`frontend/dist/`。
- 检查 README 中的示例地址、模型名称和环境变量是否符合你的实际部署环境。
- 如果项目要对外开源，建议补充 `LICENSE` 文件。
- 如果要给他人演示，可以准备一份不含密钥的 `.env.example`。

## 许可证

当前项目尚未指定许可证。发布到 GitHub 前，请根据你的开源计划补充对应的 `LICENSE` 文件。
