# LuminaryHollow · 心光树洞

> 情绪被看见，心里就有了光。

**LuminaryHollow** 是一个有记忆、有温度、能感知情绪的 AI 对话伙伴。它不同于传统 AI 助手只做问答——它像朋友一样记得你说过的话，能察觉你的情绪变化，陪你梳理思路、记录心情，并把情绪沉淀为可视化的心情日记。

## ✨ 核心差异化卖点

| 卖点 | 说明 |
| ---- | ---- |
| 🧠 情感感知 | 对话中实时识别用户情绪，AI 回复携带情绪标签与主题色 |
| 📝 长期记忆 | 多层级记忆系统：Redis 短期窗口 + ChromaDB 长期向量记忆 + PostgreSQL 用户画像 |
| 📊 可视化心情日记 | 情绪热力图、趋势曲线、关键词云、每日摘要、AI 周报 |

## 🧩 功能模块

- **聊天主界面**：WebSocket 实时对话、流式打字机输出、5 种情绪标签彩色气泡、快捷情绪记录、"对方正在输入…"
- **记忆系统（核心）**：短期记忆（Redis 滑动窗口）/ 长期向量记忆（ChromaDB）/ 用户画像（PostgreSQL）三级记忆，AI 自动总结并自然引用过往内容
- **心情日记看板**：GitHub 风格情绪热力图、30/90 天情绪趋势折线图、每日摘要时间轴、关键词云
- **AI 周报**：每周日自动生成一周情绪趋势、高频话题、关键事件的总结文字
- **数据管理**：JWT 登录、多设备会话同步、对话数据导出（JSON/Markdown）、隐私模式

## 🛠 技术栈

| 层 | 技术 |
| ---- | ---- |
| 前端 | React + TypeScript + Vite + WebSocket + ECharts |
| 后端 | FastAPI + asyncio + WebSocket |
| 数据 | PostgreSQL（用户/画像/摘要/报表）· Redis（短期记忆/会话缓存）· ChromaDB（长期记忆向量检索） |
| AI | Ollama 本地模型（如 qwen2.5）或云端大模型 API，LLM 流式输出 |
| 部署 | Docker Compose + Nginx |

## 🚀 快速开始

### 前置要求
- Docker & Docker Compose（推荐一键部署）
- 本地开发：Node.js 18+、Python 3.11+

### 一键启动
```bash
# 在项目根目录
docker compose up -d
```

### 本地开发模式
```bash
# 后端
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8012

# 前端
cd frontend
npm install
npm run dev
```

## 📁 目录结构（目标结构）

```
LuminaryHollow/
├── README.md
├── 需求.txt                      # 原始需求
├── docs/
│   └── 需求开发文档.md        # 完整详细的需求与开发设计文档
├── backend/                 # FastAPI 后端（原型骨架）
│   ├── app/
│   │   ├── main.py          # 应用入口（路由注册 / 健康检查）
│   │   ├── config.py        # 环境配置（.env）
│   │   ├── core/            # database / redis / chroma / security / deps
│   │   ├── models/          # SQLAlchemy 模型（users/chat/memory/report）
│   │   ├── schemas/         # Pydantic Schemas
│   │   ├── api/             # REST 路由（auth/users/sessions/memories/dashboard/reports/export）
│   │   ├── ws/              # WebSocket（chat 端点 / 连接管理 / 协议）
│   │   ├── services/        # LLM 适配 / 情绪感知 / 记忆 / 看板 / 周报
│   │   └── tasks/           # APScheduler 定时任务
│   ├── alembic/             # 数据库迁移
│   ├── tests/               # pytest（认证 / 情绪解析）
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                # React 前端（原型骨架）
│   └── src/
│       ├── pages/           # login/register/chat/dashboard/memories/reports/settings
│       ├── components/      # chat / dashboard / layout / common
│       ├── ws/manager.ts    # WebSocket 管理（重连/心跳/路由）
│       ├── store/           # Zustand（auth/chat/dashboard）
│       ├── api/client.ts    # axios + token 拦截器
│       ├── theme/           # 情绪主题色
│       └── styles/          # 全局与组件样式
├── docker-compose.yml
├── nginx.conf
└── .env.example
```

## 📚 文档

- [📄 需求开发文档](./docs/需求开发文档.md) —— 项目定位、功能需求与验收标准、情绪感知与 Prompt 工程、记忆系统设计、数据库 DDL、API 设计、前端设计、测试部署方案、4 周开发路线图、风险与验收清单

## 🗓 开发路线图

4 周迭代：第 1 周后端框架与认证 → 第 2 周记忆系统与情绪感知 → 第 3 周前端界面与看板 → 第 4 周周报、部署与测试收尾。

## 📄 License

MIT
