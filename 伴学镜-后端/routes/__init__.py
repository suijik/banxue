from flask import Blueprint
from .auth import register, login, send_code, update_userinfo, get_user_info, logout
from .exam import upload_exam_paper, get_exam_analyses, get_exam_analysis_detail, delete_exam_analysis
from .mistake import (
    get_mistakes, create_mistake, update_mistake, delete_mistake, delete_mistake_group,
    get_practice_questions, update_practice_question, delete_practice_question
)
from .report import report_bp
from .qa import qa_bp

# 认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api')

auth_bp.route('/register', methods=['POST'])(register)
auth_bp.route('/login', methods=['POST'])(login)
auth_bp.route('/send_code', methods=['POST'])(send_code)
auth_bp.route('/update_userinfo', methods=['POST'])(update_userinfo)
auth_bp.route('/user/info', methods=['GET'])(get_user_info)
auth_bp.route('/logout', methods=['POST'])(logout)

# 试卷分析相关路由
auth_bp.route('/upload_exam_paper', methods=['POST'])(upload_exam_paper)
auth_bp.route('/exam_analyses', methods=['GET'])(get_exam_analyses)
auth_bp.route('/exam_analysis/<int:analysis_id>', methods=['GET'])(get_exam_analysis_detail)
auth_bp.route('/exam_analysis/<int:analysis_id>', methods=['DELETE'])(delete_exam_analysis)

# 错题本相关路由
auth_bp.route('/mistakes', methods=['GET'])(get_mistakes)
auth_bp.route('/mistakes', methods=['POST'])(create_mistake)
auth_bp.route('/mistakes/group', methods=['DELETE'])(delete_mistake_group)
auth_bp.route('/mistakes/<int:mistake_id>', methods=['PUT'])(update_mistake)
auth_bp.route('/mistakes/<int:mistake_id>', methods=['DELETE'])(delete_mistake)
auth_bp.route('/practice-questions', methods=['GET'])(get_practice_questions)
auth_bp.route('/practice-questions/<int:question_id>', methods=['PUT'])(update_practice_question)
auth_bp.route('/practice-questions/<int:question_id>', methods=['DELETE'])(delete_practice_question)

# 注册报告蓝图
auth_bp.register_blueprint(report_bp, url_prefix='/report')

# 注册答疑蓝图
auth_bp.register_blueprint(qa_bp, url_prefix='/qa')
