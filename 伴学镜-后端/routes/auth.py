from flask import request, jsonify, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import re
import random
import string
import os
import logging
import time
import hashlib
from datetime import datetime, timedelta
from extension import db, mail
from models import User, ExamAnalysis, Mistake, PracticeQuestion

logger = logging.getLogger(__name__)

# 存储验证码的字典（key: 邮箱, value: {code: 验证码, time: 时间戳})
verification_codes = {}

CODE_EXPIRE_MINUTES = 5

# 密码策略配置
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPER = True
PASSWORD_REQUIRE_LOWER = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True


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
    if not username:
        return False
    pattern = r'^[A-Za-z][A-Za-z0-9]*$'
    return re.match(pattern, username) is not None


def validate_password(password):
    """验证密码复杂度：至少8位，包含大小写字母、数字和特殊字符"""
    if not password:
        return False, "密码不能为空"
    
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"密码至少{PASSWORD_MIN_LENGTH}位"
    
    # 检查密码复杂度
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
    
    if PASSWORD_REQUIRE_UPPER and not has_upper:
        return False, "密码必须包含大写字母"
    if PASSWORD_REQUIRE_LOWER and not has_lower:
        return False, "密码必须包含小写字母"
    if PASSWORD_REQUIRE_DIGIT and not has_digit:
        return False, "密码必须包含数字"
    if PASSWORD_REQUIRE_SPECIAL and not has_special:
        return False, "密码必须包含特殊字符(!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    return True, "密码有效"


def register():
    """用户注册"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    code = data.get('code')

    # 验证用户名格式
    if not validate_username(username):
        return jsonify({'success': False, 'message': '用户名只能由大小写字母和数字组成，且必须以字母开头'}), 400

    # 增强密码验证
    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400

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
            username=username,
            email=email,
            password=generate_password_hash(password)  # 密码哈希存储
        )
        db.session.add(new_user)
        db.session.commit()
        # 删除已使用的验证码
        if email in verification_codes:
            del verification_codes[email]
        
        logger.info(f"用户 {username} 注册成功")
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
    """用户登录"""
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
    if user and check_password_hash(user.password, password):  # 安全比对
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
    """发送验证码"""
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
        logger.info(f"验证码邮件已发送到 {email}")
        return jsonify({'success': True, 'message': '验证码已发送'}), 200
    except Exception as e:
        logger.error(f'邮件发送失败: {e}')
        return jsonify({'success': False, 'message': '邮件发送失败，请检查邮箱配置'}), 500


def update_userinfo():
    """更新用户信息（用户名、头像和密码）- 优化版"""
    logger.info("收到更新用户信息的请求")
    data = request.json

    # 安全日志 - 绝不记录密码，头像数据只记录长度
    safe_log_data = {}
    for k, v in data.items():
        if k == 'password':
            safe_log_data[k] = '***[密码已隐藏]***'
        elif k == 'avatar' and v and len(str(v)) > 50:
            safe_log_data[k] = f'[头像数据，长度: {len(str(v))}字符]'
        else:
            safe_log_data[k] = v
    logger.info(f"接收到的数据: {safe_log_data}")

    # 获取当前用户名
    username = data.get('username')
    if not username:
        logger.error("错误：用户名不能为空")
        return jsonify({'success': False, 'message': '用户名不能为空'}), 400

    try:
        # 根据用户名获取当前用户
        user = User.query.filter_by(username=username).first()
        if not user:
            logger.error(f"错误：找不到用户 {username}")
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        # 更新用户名
        new_username = data.get('new_username')
        if new_username and new_username != username:
            # 验证新用户名格式
            if not validate_username(new_username):
                return jsonify({'success': False, 'message': '用户名只能由大小写字母和数字组成，且必须以字母开头'}), 400
            
            # 检查新用户名是否已存在
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user.id:
                logger.error(f"错误：用户名 {new_username} 已被使用")
                return jsonify({'success': False, 'message': '该用户名已被使用'}), 400

            user.username = new_username
            logger.info(f"已更新用户名从 {username} 到 {new_username}")

        # 更新密码（如果提供）
        new_password = data.get('password')
        if new_password:
            valid, msg = validate_password(new_password)
            if not valid:
                logger.error(f"密码验证失败: {msg}")
                return jsonify({'success': False, 'message': msg}), 400
            
            user.password = generate_password_hash(new_password)  # 密码哈希存储
            logger.info(f"已更新用户 {username} 的密码")

        # 更新头像（如果提供）
        avatar = data.get('avatar')
        if avatar:
            # 检查是否是Base64数据
            if avatar.startswith('data:image'):
                logger.info(f"接收到Base64编码的头像数据")

                # 转换为URL路径存储
                file_path = save_base64_image(avatar, username)
                if file_path:
                    user.avatar = file_path
                    logger.info(f"已保存用户 {username} 的头像到文件: {file_path}")
                else:
                    logger.error(f"头像保存失败")
                    return jsonify({'success': False, 'message': '头像保存失败'}), 500
            else:
                logger.info(f"接收到头像URL")
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
            elif 'image/webp' in header:
                img_format = 'webp'
            elif 'image/gif' in header:
                img_format = 'gif'
        else:
            encoded = base64_data
            img_format = 'png'  # 默认使用png
        
        # 生成安全的文件名
        timestamp = int(time.time())
        # 使用哈希确保文件名唯一和安全
        safe_username = re.sub(r'[^a-zA-Z0-9]', '_', username)
        filename = f"{safe_username}_{timestamp}.{img_format}"
        file_path = os.path.join(upload_dir, filename)
        
        # 解码并写入文件
        import base64
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(encoded))
        
        # 返回可访问的URL路径
        return f"/static/uploads/avatars/{filename}"
    except Exception as e:
        logger.error(f"保存图片失败: {e}")
        return None


def generate_password_reset_token(email):
    """生成密码重置令牌"""
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            return None
        
        # 使用时间戳和用户ID生成临时令牌
        timestamp = str(int(datetime.utcnow().timestamp()))
        raw_token = f"{user.id}:{timestamp}:{user.email}"
        token = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 存储到数据库（需要先添加reset_token字段和reset_token_expiry字段）
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        
        logger.info(f"为用户 {user.username} 生成密码重置令牌")
        return token
    except Exception as e:
        logger.error(f"生成密码重置令牌失败: {e}")
        return None


def send_password_reset_email():
    """发送密码重置邮件"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': '邮箱不能为空'}), 400
    
    # 生成重置令牌
    token = generate_password_reset_token(email)
    if not token:
        return jsonify({'success': False, 'message': '该邮箱未注册'}), 404
    
    # 发送重置邮件
    reset_url = f"http://localhost:5000/reset-password?token={token}"
    msg = Message(
        subject='密码重置',
        sender='3444793531@qq.com',
        recipients=[email]
    )
    msg.body = f'''您收到了密码重置请求。
    
请点击以下链接重置密码（24小时内有效）：
{reset_url}

如果您没有请求重置密码，请忽略此邮件。
'''
    
    try:
        mail.send(msg)
        logger.info(f"密码重置邮件已发送到 {email}")
        return jsonify({'success': True, 'message': '密码重置链接已发送到您的邮箱'}), 200
    except Exception as e:
        logger.error(f'密码重置邮件发送失败: {e}')
        return jsonify({'success': False, 'message': '邮件发送失败'}), 500


def reset_password():
    """使用Token重置密码"""
    data = request.json
    token = data.get('token')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not token or not new_password:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400
    
    # 验证密码复杂度
    valid, msg = validate_password(new_password)
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    try:
        # 查找对应的用户
        user = User.query.filter_by(reset_token=token).first()
        if not user:
            return jsonify({'success': False, 'message': '无效的令牌'}), 400
        
        if user.reset_token_expiry < datetime.utcnow():
            return jsonify({'success': False, 'message': '令牌已过期，请重新申请'}), 400
        
        # 更新密码
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        logger.info(f"用户 {user.username} 密码重置成功")
        return jsonify({'success': True, 'message': '密码重置成功'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"密码重置失败: {e}")
        return jsonify({'success': False, 'message': '密码重置失败'}), 500


def verify_token():
    """验证重置令牌是否有效"""
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({'success': False, 'message': '缺少令牌'}), 400
    
    try:
        user = User.query.filter_by(reset_token=token).first()
        if not user:
            return jsonify({'success': False, 'message': '无效的令牌'}), 400
        
        if user.reset_token_expiry < datetime.utcnow():
            return jsonify({'success': False, 'message': '令牌已过期'}), 400
        
        return jsonify({'success': True, 'message': '令牌有效'}), 200
    except Exception as e:
        logger.error(f"验证令牌失败: {e}")
        return jsonify({'success': False, 'message': '验证失败'}), 500


def change_password():
    """已登录用户修改密码"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        data = request.json
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not old_password or not new_password:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        # 验证旧密码
        if not check_password_hash(user.password, old_password):
            return jsonify({'success': False, 'message': '原密码错误'}), 400
        
        # 验证新密码
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400
        
        valid, msg = validate_password(new_password)
        if not valid:
            return jsonify({'success': False, 'message': msg}), 400
        
        # 更新密码
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        logger.info(f"用户 {user.username} 修改密码成功")
        return jsonify({'success': True, 'message': '密码修改成功'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"修改密码失败: {e}")
        return jsonify({'success': False, 'message': '修改密码失败'}), 500