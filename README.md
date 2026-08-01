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
