import os
from datetime import timedelta
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """应用配置类 - 所有敏感信息从环境变量读取"""
    
    # ==================== 基础配置 ====================
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY 环境变量未设置！")
    
    # ==================== 数据库配置 ====================
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(basedir, 'instance')
    os.makedirs(instance_path, exist_ok=True)
    
    # 数据库连接（支持多种数据库）
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # 默认使用SQLite
        db_file = os.environ.get('DB_FILE', 'app.db')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(instance_path, db_file)}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'False').lower() == 'true'
    
    # ==================== JWT配置 ====================
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY 环境变量未设置！")
    
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 7))
    )
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = os.environ.get('JWT_COOKIE_SECURE', 'False').lower() == 'true'
    JWT_COOKIE_CSRF_PROTECT = os.environ.get('JWT_COOKIE_CSRF_PROTECT', 'True').lower() == 'true'
    
    # ==================== 邮件配置 ====================
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.qq.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        logger.warning("邮件服务未配置 (MAIL_USERNAME 或 MAIL_PASSWORD 未设置)")
    
    # ==================== AI模型配置 ====================
    # 智谱AI (ZhipuAI)
    ZHIPUAI_API_KEY = os.environ.get('ZHIPUAI_API_KEY')
    if not ZHIPUAI_API_KEY:
        logger.warning("ZHIPUAI_API_KEY 未设置，AI功能可能不可用")
    
    ZHIPUAI_MODEL = os.environ.get('ZHIPUAI_MODEL', 'glm-4')
    ZHIPUAI_VISION_MODEL = os.environ.get('ZHIPUAI_VISION_MODEL', 'glm-4v-plus')
    ZHIPUAI_TIMEOUT = int(os.environ.get('ZHIPUAI_TIMEOUT', 30))
    ZHIPUAI_MAX_TOKENS = int(os.environ.get('ZHIPUAI_MAX_TOKENS', 2048))
    ZHIPUAI_TEMPERATURE = float(os.environ.get('ZHIPUAI_TEMPERATURE', 0.7))
    ZHIPUAI_TOP_P = float(os.environ.get('ZHIPUAI_TOP_P', 0.9))
    
    # DeepSeek API配置（备选）
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    if DEEPSEEK_API_KEY:
        DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com')
        DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
    else:
        logger.info("DEEPSEEK_API_KEY 未设置，将使用智谱AI")
        DEEPSEEK_API_URL = None
        DEEPSEEK_MODEL = None
    
    # OpenAI配置（可选）
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_API_URL = os.environ.get('OPENAI_API_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # 默认AI提供商
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'zhipuai')  # zhipuai, deepseek, openai
    
    # ==================== 百度OCR配置 ====================
    BAIDU_OCR_API_KEY = os.environ.get('BAIDU_OCR_API_KEY')
    BAIDU_OCR_SECRET_KEY = os.environ.get('BAIDU_OCR_SECRET_KEY')
    
    if BAIDU_OCR_API_KEY and BAIDU_OCR_SECRET_KEY:
        BAIDU_OCR_URL = os.environ.get('BAIDU_OCR_URL', 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic')
        BAIDU_OCR_TIMEOUT = int(os.environ.get('BAIDU_OCR_TIMEOUT', 10))
    else:
        logger.warning("百度OCR未配置 (BAIDU_OCR_API_KEY 或 BAIDU_OCR_SECRET_KEY 未设置)")
    
    # ==================== 文件上传配置 ====================
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(basedir, 'static', 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx'}
    MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', 5 * 1024 * 1024))  # 5MB
    
    # ==================== 安全配置 ====================
    # CORS设置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS]
    
    # 速率限制
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # 会话配置
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ==================== 应用配置 ====================
    APP_NAME = os.environ.get('APP_NAME', '智能学习平台')
    APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    TESTING = os.environ.get('TESTING', 'False').lower() == 'true'
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', os.path.join(basedir, 'logs', 'app.log'))
    
    # ==================== 验证配置完整性 ====================
    @classmethod
    def validate(cls):
        """验证必要的配置项是否已设置"""
        required_vars = ['SECRET_KEY', 'JWT_SECRET_KEY']
        missing = []
        
        for var in required_vars:
            if not getattr(cls, var, None):
                missing.append(var)
        
        if missing:
            raise ValueError(f"缺少必要的环境变量: {', '.join(missing)}")
        
        # 检查AI服务是否可用
        if not cls.ZHIPUAI_API_KEY and not cls.DEEPSEEK_API_KEY and not cls.OPENAI_API_KEY:
            logger.warning("所有AI服务均未配置，AI功能将不可用")
        
        return True

# ==================== 环境特定配置 ====================

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    JWT_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False
    
    def __init__(self):
        # 开发环境可以使用默认值
        if not os.environ.get('SECRET_KEY'):
            os.environ['SECRET_KEY'] = 'dev-secret-key-change-in-production'
        if not os.environ.get('JWT_SECRET_KEY'):
            os.environ['JWT_SECRET_KEY'] = 'dev-jwt-secret-key-change-in-production'
        # 加载.env.dev文件
        load_dotenv('.env.dev')

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False
    
    # 使用测试用的API密钥
    ZHIPUAI_API_KEY = os.environ.get('TEST_ZHIPUAI_API_KEY', 'test-key')
    DEEPSEEK_API_KEY = os.environ.get('TEST_DEEPSEEK_API_KEY', 'test-key')

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    JWT_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    RATELIMIT_ENABLED = True
    
    # 生产环境必须从环境变量读取
    def __init__(self):
        # 强制要求所有敏感配置
        required_vars = ['SECRET_KEY', 'JWT_SECRET_KEY', 'MAIL_PASSWORD', 'ZHIPUAI_API_KEY']
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            raise ValueError(f"生产环境缺少必要的环境变量: {', '.join(missing)}")

# ==================== 配置工厂 ====================

def get_config():
    """根据环境获取配置"""
    env = os.environ.get('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
        'default': DevelopmentConfig
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    config = config_class()
    
    # 验证配置
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"配置验证失败: {e}")
        raise
    
    return config

# ==================== 配置使用示例 ====================

def get_ai_config():
    """获取AI服务配置"""
    provider = Config.AI_PROVIDER
    
    if provider == 'zhipuai' and Config.ZHIPUAI_API_KEY:
        return {
            'provider': 'zhipuai',
            'api_key': Config.ZHIPUAI_API_KEY,
            'model': Config.ZHIPUAI_MODEL,
            'vision_model': Config.ZHIPUAI_VISION_MODEL,
            'timeout': Config.ZHIPUAI_TIMEOUT,
            'max_tokens': Config.ZHIPUAI_MAX_TOKENS,
            'temperature': Config.ZHIPUAI_TEMPERATURE,
            'top_p': Config.ZHIPUAI_TOP_P
        }
    elif provider == 'deepseek' and Config.DEEPSEEK_API_KEY:
        return {
            'provider': 'deepseek',
            'api_key': Config.DEEPSEEK_API_KEY,
            'base_url': Config.DEEPSEEK_API_URL,
            'model': Config.DEEPSEEK_MODEL
        }
    elif provider == 'openai' and Config.OPENAI_API_KEY:
        return {
            'provider': 'openai',
            'api_key': Config.OPENAI_API_KEY,
            'base_url': Config.OPENAI_API_URL,
            'model': Config.OPENAI_MODEL
        }
    else:
        # 自动选择一个可用的服务
        if Config.ZHIPUAI_API_KEY:
            return {
                'provider': 'zhipuai',
                'api_key': Config.ZHIPUAI_API_KEY,
                'model': Config.ZHIPUAI_MODEL
            }
        elif Config.DEEPSEEK_API_KEY:
            return {
                'provider': 'deepseek',
                'api_key': Config.DEEPSEEK_API_KEY,
                'base_url': Config.DEEPSEEK_API_URL,
                'model': Config.DEEPSEEK_MODEL
            }
        elif Config.OPENAI_API_KEY:
            return {
                'provider': 'openai',
                'api_key': Config.OPENAI_API_KEY,
                'base_url': Config.OPENAI_API_URL,
                'model': Config.OPENAI_MODEL
            }
        else:
            raise ValueError("没有可用的AI服务配置")