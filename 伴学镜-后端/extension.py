from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

# 创建扩展对象
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
jwt = JWTManager()