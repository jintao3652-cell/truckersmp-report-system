from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class RegistrationForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField("邮箱", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("密码", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("确认密码", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("注册")


class LoginForm(FlaskForm):
    username_or_email = StringField("用户名或邮箱", validators=[DataRequired()])
    password = PasswordField("密码", validators=[DataRequired()])
    remember = BooleanField("记住我")
    submit = SubmitField("登录")


class RequestResetForm(FlaskForm):
    email = StringField("邮箱", validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField("发送重置邮件")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("新密码", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("确认密码", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("重置密码")


class UploadForm(FlaskForm):
    report_id = StringField("举报ID", validators=[DataRequired(), Length(max=64)])
    title = StringField("标题", validators=[DataRequired(), Length(max=140)])
    description = TextAreaField("说明", validators=[Optional(), Length(max=5000)])
    video_file = FileField(
        "视频文件",
        validators=[FileRequired(), FileAllowed(["mp4", "mov", "mkv", "webm", "avi"], "仅支持常见视频格式")],
    )
    submit = SubmitField("上传")
