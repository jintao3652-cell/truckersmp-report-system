# TruckersMP 举报视频存储网站

这是面向 Linux 服务器的 Flask 基础骨架，包含注册/登录、视频上传、公开视频详情、管理员审核和过期清理脚本。

## 开发启动

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Linux 部署建议

- 代码目录：`/var/www/truckersmp-report-site`
- 正式视频目录：`/sdk/truckersmp-videos`
- Web 进程：`gunicorn -c gunicorn.conf.py wsgi:app`
- Nginx 静态与反向代理：`deploy/nginx.conf`
- systemd 服务：`deploy/truckersmp-report-site.service`
- 视频文件由 Flask 的 `media` 路由提供，Nginx 仅负责反向代理

## 环境变量

- `SECRET_KEY`
- `DATABASE_URL`
- `UPLOAD_FOLDER`
- `VIDEO_FOLDER`
- `MAX_CONTENT_LENGTH`

## 当前状态

- 用户系统骨架已完成
- 视频上传与展示基础链路已完成
- 管理后台入口已完成
- 每日清理脚本已完成

后续可以继续补：FFmpeg 缩略图、分片上传、邮件找回密码、分页搜索和更完整的审核流。
