# CareerPilot

AI 简历诊断、岗位匹配和简历优化。V1.0 是前后端分离的模块化单体：Vue 3 前端，FastAPI 后端，MySQL 存储。

长任务会写入 `ai_tasks`，由后端进程内的执行器异步完成。接口立即返回任务 ID，页面轮询状态。请使用单个后端进程；多个 worker 不能共享这个进程内队列。

## 本地开发

1. 复制环境变量：

```bash
copy .env.example .env
```

2. 启动 MySQL。可以用项目里的 Compose 只起数据库：

```bash
docker compose up -d mysql
```

3. 后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

4. 前端：

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 。Vite 会把 `/api` 代理到 `http://127.0.0.1:8000`。

在 `.env` 中填写：

- `LLM_BASE_URL`：OpenAI 兼容地址，需要包含 `/v1`，例如 `https://api.openai.com/v1`
- `LLM_API_KEY`
- `LLM_MODEL`

未配置 `LLM_API_KEY` 时，解析、诊断、岗位解析和优化任务会失败，并提示缺少密钥。岗位匹配在模型输出无法通过校验时，仍保留规则分。

## Docker

在项目根目录准备好 `.env` 后执行：

```bash
docker compose up --build
```

浏览器访问 http://localhost:8080 。Nginx 托管前端，并把 `/api/` 转发到后端。

## 测试

```bash
cd backend
pytest
```

测试使用内存 SQLite，不需要 MySQL 或真实模型密钥。

## 说明

- 上传只接受 PDF 和 DOCX，最大 10 MB，并校验文件头。
- 扫描版 PDF 不会做 OCR。
- 简历和 JD 会作为不可信文本送给模型。诊断、匹配和优化结论需要能追溯到原文；缺少数字时会提示补充真实数据，而不是编造。
- 历史诊断和匹配报告绑定当时的简历版本与岗位快照。
