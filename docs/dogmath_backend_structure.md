
# DogMath Backend Architecture

_A minimal yet extensible backend blueprint covering the 0 → 1 MVP and future scale‑out._

---

## 1. High‑Level Architecture

```mermaid
flowchart TD
    subgraph Client Side
        FE[Frontend (React/Next.js)]
    end

    subgraph Core Backend
        API[api_service\n(FastAPI + Auth + Orchestrator)]
        PG[(PostgreSQL)]
        RS[(Redis Streams / PubSub)]
        MQ[[Redis Streams\nqueue.image2json / queue.json2video]]
        IO[(MinIO – S3 compatible)]
        W1[worker_img2json]
        W2[worker_render]
    end

    FE -- REST / WS --> API
    API -- SQL --> PG
    API -- publish progress --> RS
    API -- XADD --> MQ
    W1 -- consume --> MQ
    W1 -- put JSON --> IO
    W1 -- UPDATE --> PG
    W1 -- progress --> RS
    W1 -- XADD --> MQ
    W2 -- consume --> MQ
    W2 -- get JSON --> IO
    W2 -- put Video --> IO
    W2 -- UPDATE --> PG
    W2 -- progress --> RS
    IO -- presigned URL --> FE
```

---

## 2. Component Overview (0‑1 Stage)

| Container            | Tech / Port | Main Duties                                                     |
|----------------------|-------------|-----------------------------------------------------------------|
| **api_service**      | FastAPI :8000| REST + WebSocket, Auth (JWT), Job orchestration                 |
| **worker_img2json**  | Python      | Consume `queue.image2json`, call LLM/OCR, generate MVS JSON      |
| **worker_render**    | Python + FFmpeg | Consume `queue.json2video`, render blackboard & compose video |
| **postgres**         | Postgres :5432| State DB – users, jobs, billing, quotas                         |
| **redis**            | Redis :6379 | Task queues, progress cache, Pub/Sub                            |
| **minio**            | MinIO :9000 | Object storage – images, JSON, videos                           |

> **Note** – All containers can live on one 16 vCPU / 64 GB host. Storage types share the same machine but remain **logical boundaries** for future migration.

---

## 3. External API Spec (MVP)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/auth/signup`            | Register → JWT |
| `POST` | `/auth/login`             | Login → JWT |
| `POST` | `/jobs`                   | Upload image, create job |
| `GET`  | `/jobs/{job_id}`          | Get job status / percent / result URL |
| `GET`  | `/results/{job_id}/preview` | 302 to presigned video |
| `WS`   | `/ws/progress/{job_id}`   | Real‑time progress push |

---

## 4. Core Data Models

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

## 5. Queue Protocol

| Stream                 | Fields                    | Producer → Consumer            |
|------------------------|---------------------------|--------------------------------|
| `queue.image2json`     | `job_id`, `image_key`     | api_service → worker_img2json  |
| `queue.json2video`     | `job_id`, `json_key`      | worker_img2json → worker_render|
| `progress` (Pub/Sub)   | `job_id`, `percent`, `stage` | Workers → api_service (WS) |

Workers use `SELECT … FOR UPDATE SKIP LOCKED`; three retries before marking `FAILED`.

---

## 6. Rendering Pipeline

1. **Parse** MathVideoScript → segment timeline  
2. **Audio TTS** → `audio_*.wav`  
3. **Digital‑teacher video** → `teacher_*.mp4`  
4. **Blackboard SVG → video** → `blackboard_*.mp4`  
5. **FFmpeg compose** segment triplets → `final_{job_id}.mp4`  
6. **Upload** to MinIO, clean temp files via cron.

---

## 7. Docker‑Compose (excerpt)

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

## 8. Performance Baseline (5 concurrent users)

- End‑to‑end per job ≈ **50–70 s**  
- Queue wait < **30 s** under 10 jobs /minute  
- Peak CPU: **10 vCPU** (< 65 % of 16‑core host)  
- Memory footprint: **< 15 GB** total

---

## 9. Security & Ops

| Area        | Practice |
|-------------|----------|
| Transport   | HTTPS; presigned URLs expire ≤ 72 h |
| Storage     | bcrypt passwords; secrets via env vars |
| Permissions | JWT + RBAC; single‑use download token |
| Monitoring  | Prometheus (CPU/Mem/Streams), Grafana alerts |
| Backups     | `wal-g` for Postgres; MinIO object lifecycle |
| Cleanup     | Daily cron removes temp & expired videos |

---

## 10. Future Roadmap

| Scale milestone | Action |
|-----------------|--------|
| **>20 conc. users** | Add worker_render replicas or GPU nodes; move Redis to dedicated instance |
| **>100 conc. users** | Split Auth/Billing micro‑service; RabbitMQ/Kafka replace Redis Streams |
| Multi‑region   | Migrate MinIO → cloud S3 + CDN; Postgres → Aurora |
| GPU encoding   | FFmpeg with `h264_nvenc`; self‑hosted GPU pool |

---

> **TL;DR** – One host, six containers, clear storage separation. Horizontal scaling by adding Worker replicas or upgrading storage layers requires **zero** business‑logic rewrite.

