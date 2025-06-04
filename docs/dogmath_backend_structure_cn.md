
# DogMath 后端架构（中文说明）

_一套覆盖 **0 → 1 MVP** 以及未来扩容的最小可用且可扩展后台蓝图_

---

## 1. 整体架构

```mermaid
flowchart TD
    subgraph 客户端
        FE[前端页面 (React/Next.js)]
    end

    subgraph 核心后台
        API[api_service\n(FastAPI + Auth + Orchestrator)]
        PG[(PostgreSQL)]
        RS[(Redis Streams / PubSub)]
        MQ[[Redis Streams\nqueue.image2json / queue.json2video]]
        IO[(MinIO – 兼容 S3)]
        W1[worker_img2json]
        W2[worker_render]
    end

    FE -- REST / WS --> API
    API -- SQL --> PG
    API -- 推送进度 --> RS
    API -- XADD --> MQ
    W1 -- 消费 --> MQ
    W1 -- 上传 JSON --> IO
    W1 -- UPDATE --> PG
    W1 -- 进度 --> RS
    W1 -- XADD --> MQ
    W2 -- 消费 --> MQ
    W2 -- 下载 JSON --> IO
    W2 -- 上传视频 --> IO
    W2 -- UPDATE --> PG
    W2 -- 进度 --> RS
    IO -- 预签名 URL --> FE
```

---

## 2. 组件概览（0‑1 阶段）

| 容器/服务             | 技术 / 端口       | 主要职责                                               |
|-----------------------|-------------------|--------------------------------------------------------|
| **api_service**       | FastAPI :8000     | REST + WebSocket；账号认证（JWT）；任务编排            |
| **worker_img2json**   | Python            | 消费 `queue.image2json`；调用 LLM/OCR，生成 MVS JSON   |
| **worker_render**     | Python + FFmpeg   | 消费 `queue.json2video`；渲染黑板/数字人并合成视频     |
| **postgres**          | Postgres :5432    | 状态库：用户、任务、计费、配额                         |
| **redis**             | Redis :6379       | 任务队列、进度缓存、Pub/Sub                            |
| **minio**             | MinIO :9000       | 对象存储：图片、JSON、视频                             |

> **说明**：以上容器可部署在同一台 16 vCPU / 64 GB 服务器上。  
> 存储物理同机无妨，但保持「关系 / 缓存 / 对象」三类**逻辑边界**，便于未来迁移。

---

## 3. 对外 API 规范（MVP）

| 方法 | 路径 | 功能说明 |
|------|------|----------|
| `POST` | `/auth/signup`            | 注册，返回 JWT |
| `POST` | `/auth/login`             | 登录，返回 JWT |
| `POST` | `/jobs`                   | 上传题图并创建任务 |
| `GET`  | `/jobs/{job_id}`          | 查询任务状态 / 进度 / 结果 URL |
| `GET`  | `/results/{job_id}/preview` | 302 重定向到视频预签名 URL |
| `WS`   | `/ws/progress/{job_id}`   | 实时推送进度 `{percent, stage}` |

---

## 4. 核心数据模型

```sql
CREATE TABLE "user" (
  id            BIGSERIAL PRIMARY KEY,
  email         TEXT UNIQUE,
  password_hash TEXT,
  quota         INT DEFAULT 10,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE job (
  id         BIGSERIAL PRIMARY KEY,
  user_id    BIGINT REFERENCES "user"(id),
  status     TEXT,          -- WAIT_IMAGE2JSON / WAIT_JSON2VIDEO / FINISHED / FAILED
  percent    NUMERIC(5,2),
  image_key  TEXT,
  json_key   TEXT,
  video_key  TEXT,
  error_msg  TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 5. 队列协议

| Stream                 | 字段                           | 生产者 → 消费者                      |
|------------------------|--------------------------------|--------------------------------------|
| `queue.image2json`     | `job_id`, `image_key`          | api_service → worker_img2json        |
| `queue.json2video`     | `job_id`, `json_key`           | worker_img2json → worker_render      |
| `progress` (Pub/Sub)   | `job_id`, `percent`, `stage`   | 任意 Worker → api_service (WS)       |

> Worker 拉流后先 `SELECT … FOR UPDATE SKIP LOCKED`；重试 ≥ 3 次即标记 `FAILED`。

---

## 6. 渲染流水线

1. **解析** MathVideoScript，按时间轴切段  
2. **语音** TTS 生成 `audio_*.wav`  
3. **数字人** 视频 `teacher_*.mp4`  
4. **黑板** SVG → 视频 `blackboard_*.mp4`  
5. **FFmpeg 合成** 三路叠加 → `final_{job_id}.mp4`  
6. **上传** 到 MinIO，定时 cron 清理临时文件

---

## 7. Docker‑Compose（核心片段）

```yaml
services:
  api:
    build: ./api_service
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgres://postgres:dogmath@postgres:5432/postgres
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: http://minio:9000
      AWS_ACCESS_KEY_ID: minio
      AWS_SECRET_ACCESS_KEY: minio123
    depends_on: [postgres, redis, minio]

  worker_img2json:
    build: ./workers/img2json
    depends_on: [redis, minio]

  worker_render:
    build: ./workers/render
    deploy:
      resources:
        limits: { cpus: "4", memory: "4G" }
    depends_on: [redis, minio]

  postgres:
    image: postgres:16
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment: { POSTGRES_PASSWORD: dogmath }

  redis:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio123
    volumes: ["minio:/data"]
    ports: ["9000:9000", "9001:9001"]

volumes:
  pgdata:
  minio:
```

---

## 8. 性能基线（5 个并发用户）

| 指标                    | 目标值             | 估算结果 |
|-------------------------|--------------------|----------|
| 单任务端到端耗时        | ≤ 90 s            | 50–70 s |
| 队列等待                | ≤ 30 s            | 0–10 s  |
| 峰值 CPU 使用           | ≤ 65 % (16 核)    | ~10 vCPU |
| 内存占用               | ≤ 15 GB            | < 15 GB |

---

## 9. 安全与运维

| 领域     | 实践 |
|----------|------|
| 传输     | 全站 HTTPS；预签名 URL 72 h 失效 |
| 存储     | 密码 bcrypt；密钥注入容器环境变量 |
| 权限     | JWT + RBAC；下载链接一次性 Token |
| 监控     | Prometheus + Grafana + Loki |
| 备份     | Postgres 使用 wal-g；MinIO 对象生命周期 |
| 清理     | 日常 cron 删除临时 & 过期视频 |

---

## 10. 未来演进路线

| 规模里程碑        | 动作 |
|-------------------|------|
| **> 20 并发用户** | 扩副本 `worker_render` 或 GPU 节点；Redis 独立实例 |
| **> 100 并发用户**| 抽离 Auth/Billing 微服务；用 RabbitMQ/Kafka 替换 Redis Streams |
| 跨区域部署        | MinIO 迁移云 S3 + CDN；Postgres → Aurora |
| GPU 加速          | FFmpeg `h264_nvenc`；自建 GPU 池 |

---

> **总结**：单机 6 容器即可跑通全流程；按「复制 Worker / 升级存储」即可轻松横向扩容且无需改动业务逻辑。
