# TruckersMP 举报视频存储系统

Flask 应用，支持注册登录、邮件找回密码、登录/上传限流、视频上传、用户容量配额、管理员审核、登录审计和过期清理。

## 开发启动

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## 生产部署

生产环境必须设置随机 `SECRET_KEY`、`ENVIRONMENT=production` 和 `AUTO_CREATE_DB=0`。使用 Flask-Migrate 更新数据库：

```bash
flask --app manage.py db upgrade
```

安装 FFmpeg 后，上传会通过 `ffprobe` 校验视频流并读取时长；设置 `REQUIRE_FFPROBE=1` 强制校验。默认每个用户 20 GiB 配额，可用 `MAX_USER_STORAGE_BYTES` 调整。

视频权限由 Flask 判断，媒体文件通过 Nginx `X-Accel-Redirect` 直出。请让 Nginx 的 `alias` 与 `VIDEO_FOLDER` 一致，并确保视频目录不被公网直接映射。

启用过期清理：

```bash
sudo cp deploy/truckersmp-cleanup.service deploy/truckersmp-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now truckersmp-cleanup.timer
```

## 主要环境变量

`SECRET_KEY`、`DATABASE_URL`、`UPLOAD_FOLDER`、`VIDEO_FOLDER`、`MAX_CONTENT_LENGTH`、`MAX_USER_STORAGE_BYTES`、`FFPROBE_PATH`、`REQUIRE_FFPROBE`、`MEDIA_ACCEL_REDIRECT`、`AUTO_CREATE_DB`、`MAIL_PROVIDER`、`MAIL_USERNAME`、`MAIL_PASSWORD`、`MAIL_DEFAULT_SENDER`、`RATE_LIMIT_*`、`UPLOAD_RATE_LIMIT_*`。

## 数据库迁移

首次初始化（仅开发或新环境）：

```bash
flask --app manage.py db init
flask --app manage.py db migrate -m "initial schema"
flask --app manage.py db upgrade
```

生产环境只执行 `db upgrade`，不要依赖启动时的 `db.create_all()`。

## 首次部署检查清单

1. 创建数据库并执行 `flask --app manage.py db upgrade`。
2. 设置 `AUTO_CREATE_DB=0`、随机 `SECRET_KEY` 和 `SESSION_COOKIE_SECURE=1`。
3. 确认运行用户可读写 `UPLOAD_FOLDER` 和 `VIDEO_FOLDER`。
4. 安装并验证 `ffprobe -version`，生产建议设置 `REQUIRE_FFPROBE=1`。
5. 确认 Nginx `protected-videos` 的 `alias` 与 `VIDEO_FOLDER` 完全一致。
6. 复制并启用 cleanup service/timer，确认 `.env` 可被 systemd 读取。
7. 检查 Nginx `client_max_body_size`、HTTPS 和反向代理真实 IP 配置。

监控端点为 `/metrics`，可由 Prometheus 抓取；健康检查为 `/health`。HTTPS 示例见 `deploy/nginx-https.conf.example`。

对象存储通过 `STORAGE_BACKEND` 适配：`local` 使用本地目录，`s3` 使用 S3/MinIO（需安装 `boto3` 并配置 `STORAGE_S3_*`）。媒体处理可通过 `MEDIA_PROCESSING_ASYNC=1` 写入 `MediaJob`，由 `media_worker.py` 或 systemd timer 异步执行 ffprobe/缩略图。

保留策略由 `RETENTION_POLICY` 控制，支持 `365` 或 `default:365,reports:90,permanent:0`。上传成功会按需发送 `NOTIFY_WEBHOOK_URL` / `NOTIFY_ADMIN_EMAIL` 通知。`/metrics` 提供磁盘使用率和告警指标 `truckersmp_disk_alert`。

启用媒体 worker：
```bash
sudo cp deploy/truckersmp-media-worker.service deploy/truckersmp-media-worker.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now truckersmp-media-worker.timer
```

分片上传 API 使用 8 MiB 默认分片，单块上限由 `UPLOAD_CHUNK_MAX_BYTES` 控制（默认 16 MiB），上传会话默认 24 小时过期。可通过 `UPLOAD_SESSION_EXPIRES_SECONDS` 调整，并使用 `cleanup_upload_sessions.py` 定期清理中断上传。

已有数据库升级到当前版本时，必须依次执行所有迁移（包括 `0006_upload_session_activity`），不要直接修改已执行过的 migration 文件。

可运行本地迁移链检查：

```bash
python check_migrations.py
```

分片 API 使用 Bearer Token 或登录 Session 鉴权，并通过 API blueprint 豁免浏览器 CSRF；生产环境必须启用 HTTPS、短期 Token 和严格的用户配额。
