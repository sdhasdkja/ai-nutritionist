# AI营养师Agent

基于 LLM 多Agent协作的智能个性化营养饮食管理系统（LangGraph + RAG + Vue3 + FastAPI + MySQL + ChromaDB）。

## 功能

- **健康报告解析**：录入体检报告，自动提取血糖/血压/尿酸/胆固醇/甘油三酯并评估异常
- **个性化食谱生成**：多Agent工作流（健康分析→营养规划→食谱生成→质量审核），审核不通过自动打回重写（最多3轮）
- **RAG知识库**：ChromaDB 存储营养学知识（血糖管理/高血压/痛风/血脂/膳食指南/低GI/抗炎饮食），营养规划时语义检索增强
- **口味偏好管理**：喜欢的/不喜欢的食物、菜系、过敏食物，生成食谱时严格规避过敏原
- **用户体系**：JWT 认证，个人资料（身高体重年龄参与营养规划）

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue3 + Vite + Element Plus + TailwindCSS + Pinia |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Agent | LangGraph（多Agent状态机）+ LangChain |
| RAG | ChromaDB + 百炼 text-embedding-v3 |
| LLM | 阿里云百炼 qwen-plus（OpenAI兼容接口，`DASHSCOPE_API_KEY`） |
| 数据库 | MySQL 8.0（业务） + ChromaDB（向量） |

## 目录结构

```
ai-nutritionist/
├── backend/
│   ├── app/
│   │   ├── core/        # 配置/数据库/JWT认证
│   │   ├── models/      # SQLAlchemy 模型
│   │   ├── schemas/     # Pydantic 模式
│   │   ├── api/         # 路由: auth/users/health_reports/recipes/preferences
│   │   ├── services/    # 报告解析器 + 知识库
│   │   ├── agents/      # LangGraph 多Agent工作流
│   │   └── main.py
│   ├── knowledge_base/  # 营养知识种子数据
│   ├── requirements.txt
│   └── .env
├── frontend/            # Vue3 应用（11个页面）
└── sql/init.sql
```

## 快速启动

### 1. 数据库（已初始化可跳过）

```bash
mysql -u root -p < sql/init.sql
```

### 2. 后端

```bash
conda activate Agent_study
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

启动时自动建表 + 向量化导入营养知识库（调用百炼 embedding）。

需要环境变量 `DASHSCOPE_API_KEY`（或写入 `backend/.env` 的 `LLM_API_KEY`）。

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 访问

- 前端: http://localhost:5173
- API文档: http://localhost:8000/docs
- 测试账号: `admin` / `admin123`（或自行注册）

## 使用流程

1. 注册/登录 → 个人资料填写身高体重年龄
2. 健康报告页粘贴体检报告文本（如：`空腹血糖 6.8 mmol/L`、`血压 135/88`、`尿酸 460 μmol/L`）
3. 口味偏好页设置喜好与过敏原
4. 我的食谱页选择报告 → AI生成（1-3分钟，4个Agent接力+审核回环）
