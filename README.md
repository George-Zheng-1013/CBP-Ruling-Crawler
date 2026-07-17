# CBP Ruling Explorer

美国海关与边境保护局（CBP）约束性预裁定数据采集、存储、检索与可视化系统。

## 项目结构

```
├── cbp-crawler/          # Python 爬虫：从 CBP CROSS API 采集裁定数据
├── cbp-ruling-explorer/  # 全栈 Web 应用：搜索、过滤、统计、导出
│   ├── backend/          # FastAPI 后端
│   └── frontend/         # React + TypeScript 前端
└── LLM/                  # LLM 实验（SGLang + Qwen）
```

## 技术栈

| 层 | 技术 |
|---|------|
| 数据采集 | Python 3.12, requests, SQLite (WAL) |
| 后端 API | FastAPI, Pydantic, Uvicorn |
| 前端 | React 18, TypeScript, Tailwind CSS, Zustand, Recharts |
| 构建 | Vite 5 |

## 快速开始

```bash
# 后端
cd cbp-ruling-explorer/backend
pip install -r requirements.txt
python run.py

# 前端
cd cbp-ruling-explorer/frontend
npm install
npm run dev
```
