"""Small dependency-free interface translation catalog."""

TRANSLATIONS = {
    "zh": {
        "site_name": "TruckersMP 视频库", "videos": "我的视频", "upload": "上传", "admin": "管理后台", "users": "用户管理",
        "login": "登录", "register": "注册", "logout": "退出登录", "language": "语言", "english": "English", "chinese": "中文",
        "home": "首页", "save": "保存", "search": "搜索", "status": "状态", "pending": "待审核", "approved": "已通过", "rejected": "已拒绝",
        "no_videos": "暂无视频", "title": "标题", "description": "描述", "report_id": "举报 ID", "choose_file": "选择视频文件", "no_file": "尚未选择文件",
        "upload_video": "上传视频", "share": "分享视频", "rejection_reason": "拒绝原因", "resubmit": "重新提交审核", "play_after_approval": "视频审核通过后才能播放或分享。",
        "original_filename": "原文件名", "none": "无", "moderation_history": "审核历史", "audit_csv": "导出审核 CSV", "all": "全部", "approve": "通过", "reject": "拒绝", "delete": "删除", "reset_share": "重置分享码",
        "role": "角色", "actions": "操作", "account_status": "账号状态", "quota": "配额", "save_role": "保存角色", "unlock": "解锁", "disable_upload": "禁止上传", "enable_upload": "恢复上传",
        "system": "系统", "reason": "原因", "ip": "IP", "source": "来源", "time": "时间", "video": "视频", "admin_user": "管理员", "uploader": "上传者",
        "used_quota": "已使用配额", "supported_formats": "支持 MP4、MOV、MKV、WebM、AVI", "chunk_upload": "使用分片上传", "upload_progress": "上传进度", "upload_failed": "上传失败",
        "confirm_delete": "确认删除此视频及其文件？", "duration": "时长", "file_size": "文件大小", "no_description": "无描述", "pending_count": "待审核", "active_tokens": "有效 Token",
        "last_used": "最后使用", "revoke": "撤销", "share_enabled": "分享已启用", "share_disabled": "分享已关闭", "reset_password": "重置密码", "forgot_password": "忘记密码？",
        "password": "密码", "confirm_password": "确认密码", "email": "邮箱", "username": "用户名", "submit": "提交", "remember_me": "记住我", "back_home": "返回首页",
        "not_found": "页面不存在", "server_error": "服务器错误", "file_too_large": "文件过大", "login_records": "登录记录", "success": "成功", "failure": "失败",
        "user_search": "用户名或邮箱", "locked_until": "锁定至", "available": "可上传", "deleted": "已删除", "media_description": "TruckersMP 举报视频",
    },
    "en": {
        "site_name": "TruckersMP Video Library", "videos": "My Videos", "upload": "Upload", "admin": "Admin", "users": "Users",
        "login": "Log in", "register": "Register", "logout": "Log out", "language": "Language", "english": "English", "chinese": "中文",
        "home": "Home", "save": "Save", "search": "Search", "status": "Status", "pending": "Pending", "approved": "Approved", "rejected": "Rejected",
        "no_videos": "No videos", "title": "Title", "description": "Description", "report_id": "Report ID", "choose_file": "Choose video file", "no_file": "No file selected",
        "upload_video": "Upload video", "share": "Share video", "rejection_reason": "Rejection reason", "resubmit": "Resubmit for review", "play_after_approval": "The video can be played or shared after approval.",
        "original_filename": "Original filename", "none": "None", "moderation_history": "Moderation history", "audit_csv": "Export audit CSV", "all": "All", "approve": "Approve", "reject": "Reject", "delete": "Delete", "reset_share": "Reset share code",
        "role": "Role", "actions": "Actions", "account_status": "Account status", "quota": "Quota", "save_role": "Save role", "unlock": "Unlock", "disable_upload": "Disable upload", "enable_upload": "Enable upload",
        "system": "System", "reason": "Reason", "ip": "IP", "source": "Source", "time": "Time", "video": "Video", "admin_user": "Administrator", "uploader": "Uploader",
        "used_quota": "Storage used", "supported_formats": "Supports MP4, MOV, MKV, WebM and AVI", "chunk_upload": "Use chunked upload", "upload_progress": "Upload progress", "upload_failed": "Upload failed",
        "confirm_delete": "Delete this video and its files?", "duration": "Duration", "file_size": "File size", "no_description": "No description", "pending_count": "Pending", "active_tokens": "Active tokens",
        "last_used": "Last used", "revoke": "Revoke", "share_enabled": "Sharing enabled", "share_disabled": "Sharing disabled", "reset_password": "Reset password", "forgot_password": "Forgot password?",
        "password": "Password", "confirm_password": "Confirm password", "email": "Email", "username": "Username", "submit": "Submit", "remember_me": "Remember me", "back_home": "Back home",
        "not_found": "Page not found", "server_error": "Server error", "file_too_large": "File too large", "login_records": "Login records", "success": "Success", "failure": "Failure",
        "user_search": "Username or email", "locked_until": "Locked until", "available": "Allowed", "deleted": "Deleted", "media_description": "TruckersMP report video",
    },
}


ERROR_TRANSLATIONS = {
    "zh": {"This field is required.": "此字段为必填项。", "Invalid email address.": "邮箱地址无效。", "Field must be equal to password.": "两次输入的密码必须一致。", "Supported video formats only": "仅支持常见视频格式。"},
    "en": {},
}


def translate(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS["zh"]).get(key, TRANSLATIONS["zh"].get(key, key))


def translate_error(lang, message):
    return ERROR_TRANSLATIONS.get(lang, {}).get(message, message)
