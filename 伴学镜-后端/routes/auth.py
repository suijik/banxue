from flask import request, jsonify, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import re
import random
import string
import os
import logging
from datetime import datetime, timedelta
from extension import db, mail
from models import User, ExamAnalysis, Mistake, PracticeQuestion

logger = logging.getLogger(__name__)

# 存储验证码的字典（key: 邮箱, value: {code: 验证码, time: 时间戳})
verification_codes = {}

CODE_EXPIRE_MINUTES = 5


def build_user_profile(user):
    """组装个人中心需要的用户资料和学习统计"""
    learning_days = max((datetime.utcnow().date() - user.created_at.date()).days + 1, 1) if user.created_at else 1
    exam_count = ExamAnalysis.query.filter_by(user_id=user.id).count()
    mistake_count = Mistake.query.filter_by(user_id=user.id).count()
    practice_count = PracticeQuestion.query.filter_by(user_id=user.id).count()
    mastered_mistake_count = Mistake.query.filter_by(user_id=user.id, is_mastered=True).count()

    subject_values = set()
    subject_values.update(
        row[0] for row in ExamAnalysis.query.with_entities(ExamAnalysis.subject)
        .filter_by(user_id=user.id).all() if row[0]
    )
    subject_values.update(
        row[0] for row in Mistake.query.with_entities(Mistake.subject)
        .filter_by(user_id=user.id).all() if row[0]
    )
    subject_values.update(
        row[0] for row in PracticeQuestion.query.with_entities(PracticeQuestion.subject)
        .filter_by(user_id=user.id).all() if row[0]
    )

    return user.to_profile_dict({
        'learning_days': int(learning_days),
        'exam_count': exam_count,
        'mistake_count': mistake_count,
        'mastered_count': mastered_mistake_count,
        'practice_count': practice_count,
        'subject_count': len(subject_values)
    })

def generate_verification_code():
    """生成6位随机验证码"""
    return ''.join(random.choices(string.digits, k=6))

def validate_username(username):
    """验证用户名：只能由大小写字母和数字组成，且必须以字母开头"""
    pattern = r'^[A-Za-z][A-Za-z0-9]*$'
    return re.match(pattern, username) is not None

def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    code = data.get('code')

    # 验证用户名格式
    if not validate_username(username):
        return jsonify({'success': False, 'message': '用户名只能由大小写字母和数字组成，且必须以字母开头'}), 400

    # 验证密码格式
    if password is None or len(password) < 8:
        return jsonify({'success': False, 'message': '密码至少8位'}), 400

    # 验证码校验（含过期检查）
    code_record = verification_codes.get(email)
    if not code_record:
        return jsonify({'success': False, 'message': '请先获取验证码'}), 400
    if code_record['code'] != code:
        return jsonify({'success': False, 'message': '验证码错误'}), 400
    if datetime.utcnow() - code_record['time'] > timedelta(minutes=CODE_EXPIRE_MINUTES):
        del verification_codes[email]
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400

    # 检查用户名和邮箱是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '邮箱已存在'}), 400

    # 创建新用户
    try:
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=generate_password_hash(data['password'])
        )
        db.session.add(new_user)
        db.session.commit()
        # 删除已使用的验证码
        del verification_codes[email]
        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': new_user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"注册失败: {e}")
        return jsonify(success=False, message="注册失败"), 500


def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # 验证用户名格式
    if not validate_username(username):
        return jsonify({'success': False, 'message': '用户名只能由大小写字母和数字组成，且必须以字母开头'}), 400

    # 验证密码格式
    if password is None or len(password) < 8:
        return jsonify({'success': False, 'message': '密码至少8位'}), 400

    # 查找用户
    user = User.query.filter_by(username=username).first()
    if user:
        # 兼容处理：先尝试用 bcrypt 验证（新注册的加密用户）
        if check_password_hash(user.password, password):
            password_matched = True
        # 如果 bcrypt 验证失败，尝试明文比对（旧用户之前存的明文密码）
        elif user.password == password:
            password_matched = True
            # 自动升级：将明文密码更新为加密密码
            user.password = generate_password_hash(password)
            db.session.commit()
            logger.info(f"用户 {username} 密码已自动升级为加密存储")
        else:
            password_matched = False

        if password_matched:
            logger.info(f"用户 {username} 登录成功")

            # 创建JWT访问令牌
            access_token = create_access_token(identity=user.id)

            return jsonify({
                'success': True,
                'message': '登录成功',
                'data': {
                    'username': user.username,
                    'email': user.email,
                    'avatar': user.avatar,
                    'access_token': access_token,
                    'profile': build_user_profile(user)
                }
            }), 200
        else:
            logger.warning(f"用户 {username} 登录失败：用户名或密码错误")
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 400
    else:
        logger.warning(f"用户 {username} 登录失败：用户名或密码错误")
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 400


@jwt_required()
def get_user_info():
    """获取当前登录用户信息"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        return jsonify({
            'success': True,
            'message': '获取用户信息成功',
            'data': build_user_profile(user)
        }), 200
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return jsonify({'success': False, 'message': '获取用户信息失败'}), 500


@jwt_required(optional=True)
def logout():
    """退出登录，当前版本以前端清理本地状态为主"""
    return jsonify({
        'success': True,
        'message': '退出登录成功'
    }), 200

def send_code():
    data = request.json
    email = data.get('email')
    logger.info(f"请求发送验证码到邮箱: {email}")

    # 生成验证码
    code = generate_verification_code()
    verification_codes[email] = {'code': code, 'time': datetime.utcnow()}
    logger.info(f"验证码已生成: {code}")

    # 发送验证码邮件
    msg = Message(
        subject='验证码',
        sender='3444793531@qq.com',
        recipients=[email]
    )
    msg.body = f'您的验证码是：{code}，请在5分钟内使用。'

    try:
        mail.send(msg)
        return jsonify({'success': True, 'message': '验证码已发送'}), 200
    except Exception as e:
        logger.error(f'邮件发送失败: {e}')
        return jsonify({'success': False, 'message': '邮件发送失败，请检查邮箱配置'}), 500

def update_userinfo():
    """更新用户信息（用户名、头像和密码）"""
    logger.info("收到更新用户信息的请求")
    data = request.json

    # 将头像数据从日志输出中排除
    log_data = {k: v if k != 'avatar' else '[头像数据已省略]' for k, v in data.items()}
    logger.info(f"接收到的数据: {log_data}")

    # 需要的字段：username（确定用户），password（可选），avatar（可选）
    username = data.get('username')
    if not username:
        logger.error("错误：用户名不能为空")
        return jsonify({'success': False, 'message': '用户名不能为空'}), 400

    try:
        # 根据用户名获取当前登录用户
        current_username = username
        user = User.query.filter_by(username=current_username).first()

        if not user:
            logger.error(f"错误：找不到用户 {current_username}")
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        # 更新用户名
        new_username = data.get('username')
        if new_username and new_username != current_username:
            # 检查新用户名是否已存在
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user.id:
                logger.error(f"错误：用户名 {new_username} 已被使用")
                return jsonify({'success': False, 'message': '该用户名已被使用'}), 400

            user.username = new_username
            logger.info(f"已更新用户名从 {current_username} 到 {new_username}")

        # 更新密码（如果提供）
        new_password = data.get('password')
        if new_password:
            if len(new_password) < 8:
                logger.error("错误：密码长度不足")
                return jsonify({'success': False, 'message': '密码至少8位'}), 400
            user.password = generate_password_hash(new_password)
            logger.info(f"已更新用户 {username} 的密码")

        # 更新头像（如果提供）
        avatar = data.get('avatar')
        if avatar:
            # 检查是否是Base64数据
            if avatar.startswith('data:image'):
                logger.info(f"接收到Base64编码的头像数据，长度: {len(avatar)} 字符")

                # 转换为URL路径存储
                file_path = save_base64_image(avatar, username)
                if file_path:
                    user.avatar = file_path
                    logger.info(f"已保存用户 {username} 的头像到文件: {file_path}")
                else:
                    logger.error(f"头像保存失败")
                    return jsonify({'success': False, 'message': '头像保存失败'}), 500
            else:
                logger.info(f"接收到头像URL，长度: {len(avatar)} 字符")
                user.avatar = avatar
                logger.info(f"已更新用户 {username} 的头像URL")

        db.session.commit()
        logger.info(f"成功更新用户 {username} 的信息")
        return jsonify({
            'success': True,
            'message': '用户信息更新成功',
            'data': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        logger.error(f"更新用户信息失败: {error_message}")
        return jsonify({'success': False, 'message': f'更新失败: {error_message}'}), 500

def save_base64_image(base64_data, username):
    """保存Base64图像到文件系统"""
    try:
        # 创建存储目录
        upload_dir = os.path.join('static', 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 从Base64数据中提取信息
        if ',' in base64_data:
            header, encoded = base64_data.split(',', 1)
            img_format = 'png'  # 默认格式
            if 'image/jpeg' in header:
                img_format = 'jpg'
            elif 'image/png' in header:
                img_format = 'png'
        else:
            encoded = base64_data
            img_format = 'jpg'  # 默认使用jpg
        
        # 生成文件名
        timestamp = int(time.time())
        filename = f"{username}_{timestamp}.{img_format}"
        file_path = os.path.join(upload_dir, filename)
        
        # 解码并写入文件
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(encoded))
        
        # 返回可访问的URL路径
        return f"/static/uploads/avatars/{filename}"
    except Exception as e:
        logger.error(f"保存图片失败: {e}")
        return None
