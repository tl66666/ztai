# 文件存储与后台任务

## BlobStorage 契约

application module 只持有 `BlobRef`，不拼接本地路径或 R2 URL。`BlobRef` 可安全写入
业务表或任务 payload，只包含 `backend`、`owner_id`、`object_key`、`size_bytes`、
`content_type` 和 `checksum_sha256`。adapter 必须在 `open` 与 `delete` 时再次验证
backend、owner、对象前缀和校验和。

本地开发默认使用：

```bash
JOBHUNTER_BLOB_STORAGE_BACKEND=local
JOBHUNTER_UPLOAD_FOLDER=./uploads
```

Ubuntu 生产使用 R2：

```bash
JOBHUNTER_BLOB_STORAGE_BACKEND=r2
JOBHUNTER_R2_ACCOUNT_ID=replace-with-account-id
JOBHUNTER_R2_BUCKET=jobhunter
JOBHUNTER_R2_ACCESS_KEY_ID=replace-with-access-key
JOBHUNTER_R2_SECRET_ACCESS_KEY=replace-with-secret
```

可选 `JOBHUNTER_R2_ENDPOINT_URL` 只用于兼容测试端点；正常 R2 endpoint 根据 account
ID 自动生成。凭据不得写入仓库、前端或日志。

## Durable worker

生产 API 和 worker 指向同一个 PostgreSQL：

```bash
JOBHUNTER_DATABASE_URL=postgresql+psycopg://app:secret@127.0.0.1/jobhunter
uv run python -m backend.cli
uv run python -m backend.worker
```

可调参数：

- `JOBHUNTER_JOB_LEASE_SECONDS`：默认 60。
- `JOBHUNTER_JOB_HEARTBEAT_SECONDS`：默认 20，必须小于 lease。
- `JOBHUNTER_JOB_POLL_SECONDS`：空队列轮询间隔，默认 1。
- `JOBHUNTER_JOB_MAX_ATTEMPTS`：默认 3。

任务执行使用 `SELECT ... FOR UPDATE SKIP LOCKED`（PostgreSQL）领取。worker 崩溃后，
lease 到期任务重新排队；最终尝试仍过期则标记失败。取消会让 queued/running 任务立即
进入 terminal `cancelled`，迟到的 worker 结果不会覆盖取消状态。

## HTTP 契约

- `POST /api/jobs/resume-analysis`：JSON 包含 `resume_id` 和原分析参数。
- `POST /api/jobs/document-conversion`：multipart 包含 `file` 与 `target_format`。
- `GET /api/jobs/{task_id}`：查询 owned task。
- `DELETE /api/jobs/{task_id}`：取消 owned task。
- `GET /api/jobs/{task_id}/result`：下载成功的文档转换结果。

提交端可设置 `Idempotency-Key`。相同 owner、job type 和 key 返回同一个 task，不重复
创建业务任务。原 `/api/resumes/{id}/analyze`、`/api/convert/pdf-to-word` 与
`/api/convert/word-to-pdf` 同步接口继续保留。
