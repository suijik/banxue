import os
from datetime import timedelta

class Config:
    # 数据库配置
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(basedir, 'instance')
    # 确保instance目录存在
    os.makedirs(instance_path, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(instance_path, "app.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-here')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-flask-secret-key-here')
    
    # 邮件配置（保持原有邮箱验证功能）
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = '3444793531@qq.com'
    MAIL_PASSWORD = 'zfnusxzrfnwkchae'
    
    # DeepSeek API配置
    DEEPSEEK_API_KEY = "sk-d6adae8d26da4b23b1b6e3b083208e1a"
    DEEPSEEK_API_URL = "https://api.deepseek.com"
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 百度OCR配置
    BAIDU_OCR_API_KEY = '6peKs1qmvQyqJDhfHkatqbm3'
    BAIDU_OCR_SECRET_KEY = 'f0EgmiP9vDAd6Yf0LdUvmAwW7Bn1iOIh'