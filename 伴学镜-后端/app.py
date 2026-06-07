from flask import Flask
from flask_cors import CORS
from config import Config
from extension import db, mail, migrate, jwt
import os
from sqlalchemy import inspect, text

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(Config)
    
    # 确保数据库目录存在
    db_path = os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    if db_path and not os.path.exists(db_path):
        os.makedirs(db_path)
        print(f"创建数据库目录: {db_path}")

    # 确保静态文件目录存在
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'avatars')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        print(f"创建静态文件目录: {static_dir}")

    # 初始化扩展
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    # 注册蓝图
    from routes import auth_bp
    app.register_blueprint(auth_bp)

    # 创建数据表
    with app.app_context():
        db.create_all()
        print("数据表已创建/更新")
        
        # 检查并添加avatar列
        try:
            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names() and 'avatar' not in [column['name'] for column in inspector.get_columns('users')]:
                print("添加avatar列到users表")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar VARCHAR(500) DEFAULT 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'"))
                    conn.commit()
                print("avatar列添加成功")
        except Exception as e:
            print(f"添加avatar列失败: {e}")
            
        # 检查并添加error_type列到mistakes表
        try:
            inspector = inspect(db.engine)
            if 'mistakes' in inspector.get_table_names() and 'error_type' not in [column['name'] for column in inspector.get_columns('mistakes')]:
                print("添加error_type列到mistakes表")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE mistakes ADD COLUMN error_type VARCHAR(50) DEFAULT '未归类'"))
                    conn.commit()
                print("error_type列添加成功")
        except Exception as e:
            print(f"添加error_type列失败: {e}")

        # 检查并补充错题表中的试卷归属字段
        mistake_columns = {}
        try:
            inspector = inspect(db.engine)
            if 'mistakes' in inspector.get_table_names():
                mistake_columns = {column['name']: column for column in inspector.get_columns('mistakes')}

            alter_statements = {
                'exam_analysis_id': "ALTER TABLE mistakes ADD COLUMN exam_analysis_id INTEGER",
                'exam_name_snapshot': "ALTER TABLE mistakes ADD COLUMN exam_name_snapshot VARCHAR(200)",
                'exam_image_path_snapshot': "ALTER TABLE mistakes ADD COLUMN exam_image_path_snapshot VARCHAR(500)",
                'question_no': "ALTER TABLE mistakes ADD COLUMN question_no VARCHAR(100)",
                'stem_summary': "ALTER TABLE mistakes ADD COLUMN stem_summary VARCHAR(255)"
            }

            for column_name, sql in alter_statements.items():
                if 'mistakes' in inspector.get_table_names() and column_name not in mistake_columns:
                    print(f"添加{column_name}列到mistakes表")
                    with db.engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                    print(f"{column_name}列添加成功")
        except Exception as e:
            print(f"补充mistakes扩展列失败: {e}")
        
        print(f"SQLite数据库文件位置: {os.path.abspath(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))}")
        
        # 打印表结构
        inspector = inspect(db.engine)
        for table_name in inspector.get_table_names():
            print(f"\n表 {table_name} 的结构:")
            for column in inspector.get_columns(table_name):
                print(f"  - {column['name']} ({column['type']})")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=5000)
