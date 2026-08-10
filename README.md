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

- **聊天主界面**：WebSocket 实时对话、流式打字机输出、5 种情绪标签彩色气泡、快捷情绪记录、"对方正在输入…"，前后端双重防重复保障（后端 LLM 回复重复检测 + 前端单连接 / 单 handler 消息去重）
- **拟人化陪伴**：AI 伙伴「小光」带名字与在线呼吸灯，按时段问候（早安/午安/夜深），情绪低落时"轻轻拍了拍你"，长对话每 8 轮冒出**可打卡的贴心提醒卡片**（打卡后留在本次会话历史随消息上移，刷新后不重冒、从下一轮继续）
- **WorkBuddy 工作台**：识别聊天中提到的计划（"我下午要开会"），每 5 轮冒出一张**计划提醒卡片**（"你之前说「…」——现在想起来了吗？"），可打卡完成
- **日程管理**：聊天中提到的计划（"晚上学数学""下午三点开会""我明天想跑步"等口语省略都能识别，支持想/希望/打算/要去等说法与中文数字时间）自动进日程；**没说几点时小光会反问、可一键定时间**；"下午要干什么"这类疑问句不会误记。问「今天还有什么安排 / 还有什么事没干」，小光会把今日日程连完成状态一起回复。到点前 5 分钟冒**日程提醒卡片**可打卡。日程页支持**多行批量添加**（每行一条，可带"8:30 / 明天下午3点"等，没写时间用右侧默认日期时间），周视图每天是**清晰时间轴**（大字时间、过期标红、完成划线），并带**统计概览**（今日/本周完成率进度环、近 7 天完成柱状图）与**完成热力图**（近 90 天 × 8 时段）
- **记忆系统（核心）**：短期记忆（Redis 滑动窗口）/ 长期向量记忆（ChromaDB）/ 用户画像（PostgreSQL）三级记忆，AI 自动总结并自然引用过往内容
- **心情日记看板**：情绪热力图（**天 × 时段细分**，每 3 小时一档，看清"下午总焦虑"这类阶段规律）、30/90 天情绪趋势折线图、每日摘要时间轴、关键词云
- **AI 周报**：每周日自动生成一周情绪趋势、高频话题、关键事件的总结文字
- **数据管理**：JWT 登录、多设备会话同步、对话数据导出（JSON/Markdown）、隐私模式
- **对话日志**：每次对话的用户消息 / Prompt / AI 原始回复 / 情绪解析明细落盘 `logs/chat.log`，便于复盘与排查

## 🛠 技术栈

| 层 | 技术 |
| ---- | ---- |
| 前端 | React 18 + TypeScript + Vite + WebSocket + Zustand + ECharts |
| 后端 | FastAPI + asyncio + WebSocket + SQLAlchemy + APScheduler |
| 数据 | PostgreSQL（用户/画像/摘要/报表）· Redis（短期记忆/会话缓存）· ChromaDB（长期记忆向量检索） |
| AI | Ollama 本地模型（如 qwen2.5）或云端大模型 API（如 DeepSeek），LLM 流式输出；Embedding 独立走本地 Ollama |
| 测试 | pytest（后端）· Vitest（前端） |
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

## 📁 目录结构

```
LuminaryHollow/
├── README.md
├── 需求.txt                      # 原始需求
├── .env.example                  # Docker Compose 环境变量模板
├── docker-compose.yml            # PostgreSQL / Redis / ChromaDB / 前后端 / Nginx 一键编排
├── nginx.conf                    # 反代（REST / WebSocket / 静态资源）
├── docs/
│   ├── 需求开发文档.md            # 完整需求与开发设计文档
│   └── 原型结构总览.md            # 需求→实现对照 / 关键配置 / 启动 / API 一览
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # 入口（自动建表 / 定时任务 / /health 健康检查）
│   │   ├── config.py            # pydantic-settings 环境配置（.env）
│   │   ├── core/                # database / redis / chroma / security / deps / logging_config
│   │   ├── models/              # SQLAlchemy 模型（users/chat/memory/report/schedule）
│   │   ├── schemas/             # Pydantic Schemas
│   │   ├── api/                 # REST 路由（auth/users/sessions/memories/dashboard/reports/export/schedule）
│   │   ├── ws/                  # WebSocket（chat 端点 / 连接管理 / 协议）
│   │   ├── services/            # LLM 适配 / 情绪感知 / 记忆 / 看板 / 周报
│   │   └── tasks/               # APScheduler 定时任务（周报 / 会话超时）
│   ├── alembic/                 # 数据库迁移（versions/0001_initial_schema.py、0002_schedule_items.py）
│   ├── tests/                   # pytest（认证 / 情绪解析 / 日程统计 / WebSocket 单连接，23 项）
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                    # React 18 + TypeScript + Vite 前端
│   ├── src/
│   │   ├── pages/               # login/register/chat/schedule/dashboard/memories/reports/settings
│   │   ├── components/          # chat / dashboard / layout / common
│   │   ├── ws/manager.ts        # WebSocket 管理（单连接 / 心跳 / 指数退避重连 / handler 去重）
│   │   ├── ws/manager.test.ts   # vitest 单测（消息去重 / 连接复用 / token 重建）
│   │   ├── store/               # Zustand（auth/chat/dashboard）
│   │   ├── api/client.ts        # axios + token 拦截器
│   │   ├── theme/               # 情绪主题色 / 热力图色阶 / 拟人化配置（companion.ts）
│   │   ├── utils/               # 格式化工具
│   │   └── styles/              # 全局与组件样式
│   ├── index.html
│   ├── vite.config.ts           # 开发代理（/api、/ws → :8012）
│   ├── package.json
│   ├── Dockerfile               # 多阶段构建 → Nginx 托管
│   └── .env.example
└── logs/                        # 运行时日志（chat.log / app.log，已 gitignore）
```

## 📚 文档

- [📄 需求开发文档](./docs/需求开发文档.md) —— 项目定位、功能需求与验收标准、情绪感知与 Prompt 工程、记忆系统设计、数据库 DDL、API 设计、前端设计、测试部署方案、4 周开发路线图、风险与验收清单
- [🧭 原型结构总览](./docs/原型结构总览.md) —— 需求→实现对照表、实际目录结构、关键配置（DeepSeek + 本地 Ollama Embedding）、启动方式、API 一览

## 🗓 开发路线图

4 周迭代已全部完成（当前为可运行的全栈版本）：第 1 周后端框架与认证 → 第 2 周记忆系统与情绪感知 → 第 3 周前端界面与看板 → 第 4 周周报、部署与测试收尾。

## 🧪 测试

- **后端**（pytest，23 项）：认证 / 情绪解析 / 日程统计 / WebSocket 管理 —— `cd backend && .venv\Scripts\python -m pytest`
- **前端**（vitest）：WebSocket 消息去重、连接复用、token 变化重建连接等 —— `cd frontend && npx vitest run`

## 📄 License

MIT
