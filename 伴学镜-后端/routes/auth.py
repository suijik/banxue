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
import base64
from datetime import datetime, timedelta
from functools import wraps
from extension import db, mail
from models import User, ExamAnalysis, Mistake, PracticeQuestion

logger = logging.getLogger(__name__)

# ==================== 配置常量 ====================
class AuthConfig:
    """认证配置类"""
    CODE_EXPIRE_MINUTES = 5
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPER = True
    PASSWORD_REQUIRE_LOWER = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    RESET_TOKEN_EXPIRE_HOURS = 24
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    AVATAR_MAX_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

# ==================== 存储和缓存 ====================
verification_codes = {}  # 验证码存储
login_attempts = {}  # 登录尝试记录

# ==================== 装饰器 ====================
def rate_limit(max_attempts=5, window_minutes=15):
    """限流装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端IP
            client_ip = request.remote_addr
            key = f"{client_ip}:{f.__name__}"
            
            # 简单实现：存储请求时间戳
            if not hasattr(decorated_function, '_requests'):
                decorated_function._requests = {}
            
            now = datetime.utcnow()
            window_start = now - timedelta(minutes=window_minutes)
            
            # 清理过期记录
            decorated_function._requests[key] = [
                t for t in decorated_function._requests.get(key, [])
                if t > window_start
            ]
            
            # 检查是否超过限制
            if len(decorated_function._requests.get(key, [])) >= max_attempts:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return jsonify({
                    'success': False, 
                    'message': f'操作过于频繁，请{window_minutes}分钟后再试'
                }), 429
            
            # 记录本次请求
            if key not in decorated_function._requests:
                decorated_function._requests[key] = []
            decorated_function._requests[key].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== 工具函数 ====================
def generate_verification_code():
    """生成6位随机验证码"""
    return ''.join(random.choices(string.digits, k=6))

def generate_random_token():
    """生成安全随机令牌"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def validate_username(username):
    """验证用户名：只能由大小写字母和数字组成，且必须以字母开头"""
    if not username or len(username) < 3 or len(username) > 20:
        return False
    pattern = r'^[A-Za-z][A-Za-z0-9]{2,19}$'
    return re.match(pattern, username) is not None

def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """验证密码复杂度"""
    if not password:
        return False, "密码不能为空"
    
    if len(password) < AuthConfig.PASSWORD_MIN_LENGTH:
        return False, f"密码至少{AuthConfig.PASSWORD_MIN_LENGTH}位"
    
    # 检查密码复杂度
    checks = {
        '大写字母': any(c.isupper() for c in password),
        '小写字母': any(c.islower() for c in password),
        '数字': any(c.isdigit() for c in password),
        '特殊字符': any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
    }
    
    if AuthConfig.PASSWORD_REQUIRE_UPPER and not checks['大写字母']:
        return False, "密码必须包含大写字母"
    if AuthConfig.PASSWORD_REQUIRE_LOWER and not checks['小写字母']:
        return False, "密码必须包含小写字母"
    if AuthConfig.PASSWORD_REQUIRE_DIGIT and not checks['数字']:
        return False, "密码必须包含数字"
    if AuthConfig.PASSWORD_REQUIRE_SPECIAL and not checks['特殊字符']:
        return False, "密码必须包含特殊字符(!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    return True, "密码有效"

def is_password_weak(password):
    """检测弱密码"""
    weak_passwords = [
        'password', '12345678', 'qwertyui', 'admin123',
        'letmein', 'welcome1', 'password123', 'adminadmin'
    ]
    return password.lower() in weak_passwords

def build_user_profile(user):
    """组装个人中心需要的用户资料和学习统计"""
    learning_days = max((datetime.utcnow().date() - user.created_at.date()).days + 1, 1) if user.created_at else 1
    
    # 统计数据
    stats = {
        'exam_count': ExamAnalysis.query.filter_by(user_id=user.id).count(),
        'mistake_count': Mistake.query.filter_by(user_id=user.id).count(),
        'practice_count': PracticeQuestion.query.filter_by(user_id=user.id).count(),
        'mastered_count': Mistake.query.filter_by(user_id=user.id, is_mastered=True).count()
    }
    
    # 获取涉及科目
    subject_values = set()
    for model in [ExamAnalysis, Mistake, PracticeQuestion]:
        subject_values.update(
            row[0] for row in model.query.with_entities(model.subject)
            .filter_by(user_id=user.id).all() if row[0]
        )
    
    return user.to_profile_dict({
        'learning_days': int(learning_days),
        'subject_count': len(subject_values),
        **stats
    })

def save_base64_image(base64_data, username):
    """保存Base64图像到文件系统"""
    try:
        # 验证数据大小
        if len(base64_data) > AuthConfig.AVATAR_MAX_SIZE * 4 // 3:  # Base64编码后大约增加1/3
            logger.error(f"头像文件过大: {len(base64_data)} bytes")
            return None
        
        # 创建存储目录
        upload_dir = os.path.join('static', 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 从Base64数据中提取信息
        if ',' in base64_data:
            header, encoded = base64_data.split(',', 1)
            # 验证文件类型
            if not any(img_type in header for img_type in AuthConfig.ALLOWED_AVATAR_TYPES):
                logger.error(f"不支持的图片格式: {header}")
                return None
        else:
            encoded = base64_data
        
        # 生成安全的文件名
        timestamp = int(time.time())
        safe_username = re.sub(r'[^a-zA-Z0-9]', '_', username)
        filename = f"{safe_username}_{timestamp}.png"
        file_path = os.path.join(upload_dir, filename)
        
        # 解码并写入文件
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(encoded))
        
        # 返回可访问的URL路径
        return f"/static/uploads/avatars/{filename}"
    except Exception as e:
        logger.error(f"保存图片失败: {e}")
        return None

# ==================== 核心认证函数 ====================

def register():
    """用户注册 - 增强版"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        code = data.get('code', '')
        
        # 验证必填字段
        if not all([username, password, email, code]):
            return jsonify({'success': False, 'message': '所有字段均为必填'}), 400
        
        # 验证邮箱格式
        if not validate_email(email):
            return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
        
        # 验证用户名
        if not validate_username(username):
            return jsonify({
                'success': False, 
                'message': '用户名长度为3-20位，只能由大小写字母和数字组成，且必须以字母开头'
            }), 400
        
        # 验证密码复杂度
        valid, msg = validate_password(password)
        if not valid:
            return jsonify({'success': False, 'message': msg}), 400
        
        # 检查弱密码
        if is_password_weak(password):
            return jsonify({'success': False, 'message': '密码过于简单，请使用更复杂的密码'}), 400
        
        # 验证码校验
        code_record = verification_codes.get(email)
        if not code_record:
            return jsonify({'success': False, 'message': '请先获取验证码'}), 400
        if code_record['code'] != code:
            return jsonify({'success': False, 'message': '验证码错误'}), 400
        if datetime.utcnow() - code_record['time'] > timedelta(minutes=AuthConfig.CODE_EXPIRE_MINUTES):
            del verification_codes[email]
            return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': '用户名已存在'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': '邮箱已被注册'}), 400
        
        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256:600000')
        )
        db.session.add(new_user)
        db.session.commit()
        
        # 删除已使用的验证码
        verification_codes.pop(email, None)
        
        logger.info(f"用户 {username} 注册成功 (ID: {new_user.id})")
        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"注册失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '注册失败，请稍后重试'}), 500

def login():
    """用户登录 - 增强版"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # 验证输入
        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
        
        if not validate_username(username):
            return jsonify({'success': False, 'message': '用户名格式错误'}), 400
        
        # 检查登录尝试次数
        login_key = f"{request.remote_addr}:{username}"
        attempts = login_attempts.get(login_key, {'count': 0, 'last_attempt': None})
        
        if attempts['count'] >= AuthConfig.MAX_LOGIN_ATTEMPTS:
            lock_time = attempts.get('lock_time')
            if lock_time and datetime.utcnow() - lock_time < timedelta(minutes=AuthConfig.LOCKOUT_DURATION_MINUTES):
                remaining = int((lock_time + timedelta(minutes=AuthConfig.LOCKOUT_DURATION_MINUTES) - datetime.utcnow()).total_seconds() / 60) + 1
                return jsonify({
                    'success': False,
                    'message': f'账户已锁定，请{remaining}分钟后再试'
                }), 423
        
        # 查找用户
        user = User.query.filter_by(username=username).first()
        
        # 验证密码
        if user and check_password_hash(user.password, password):
            # 登录成功，重置尝试记录
            login_attempts.pop(login_key, None)
            
            logger.info(f"用户 {username} 登录成功 (ID: {user.id})")
            
            # 创建JWT令牌
            access_token = create_access_token(
                identity=user.id,
                expires_delta=timedelta(days=7)
            )
            
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
        
        # 登录失败，记录尝试
        if login_key not in login_attempts:
            login_attempts[login_key] = {'count': 0, 'last_attempt': None, 'lock_time': None}
        
        login_attempts[login_key]['count'] += 1
        login_attempts[login_key]['last_attempt'] = datetime.utcnow()
        
        if login_attempts[login_key]['count'] >= AuthConfig.MAX_LOGIN_ATTEMPTS:
            login_attempts[login_key]['lock_time'] = datetime.utcnow()
            logger.warning(f"用户 {username} 因多次登录失败被锁定")
        
        logger.warning(f"用户 {username} 登录失败：用户名或密码错误 (尝试次数: {login_attempts[login_key]['count']})")
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
        
    except Exception as e:
        logger.error(f"登录失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '登录失败，请稍后重试'}), 500

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
        logger.error(f"获取用户信息失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '获取用户信息失败'}), 500

@jwt_required(optional=True)
def logout():
    """退出登录"""
    return jsonify({
        'success': True,
        'message': '退出登录成功'
    }), 200

@rate_limit(max_attempts=3, window_minutes=1)
def send_code():
    """发送验证码 - 增强版"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': '邮箱不能为空'}), 400
        
        if not validate_email(email):
            return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
        
        # 检查是否已存在邮箱
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': '该邮箱已被注册'}), 400
        
        # 检查发送频率
        if email in verification_codes:
            last_send = verification_codes[email].get('time')
            if last_send and datetime.utcnow() - last_send < timedelta(seconds=60):
                return jsonify({
                    'success': False,
                    'message': '发送过于频繁，请等待60秒后再试'
                }), 429
        
        # 生成验证码
        code = generate_verification_code()
        verification_codes[email] = {
            'code': code,
            'time': datetime.utcnow()
        }
        
        logger.info(f"验证码已生成: {code} (邮箱: {email})")
        
        # 发送邮件
        msg = Message(
            subject='【学习平台】验证码',
            sender='3444793531@qq.com',
            recipients=[email]
        )
        msg.body = f'''您好！

您的验证码是：{code}

请在{AuthConfig.CODE_EXPIRE_MINUTES}分钟内使用。

如果这不是您本人的操作，请忽略此邮件。

---
学习平台
'''
        
        mail.send(msg)
        logger.info(f"验证码邮件已发送到 {email}")
        
        return jsonify({
            'success': True,
            'message': '验证码已发送，请查收邮件'
        }), 200
        
    except Exception as e:
        logger.error(f'邮件发送失败: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'message': '邮件发送失败，请检查邮箱地址或稍后重试'
        }), 500

@jwt_required()
def update_userinfo():
    """更新用户信息 - 增强版"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        data = request.json
        current_username = user.username
        
        # 更新用户名
        new_username = data.get('new_username', '').strip()
        if new_username and new_username != current_username:
            if not validate_username(new_username):
                return jsonify({
                    'success': False,
                    'message': '用户名长度为3-20位，只能由大小写字母和数字组成，且必须以字母开头'
                }), 400
            
            if User.query.filter_by(username=new_username).first():
                return jsonify({'success': False, 'message': '该用户名已被使用'}), 400
            
            user.username = new_username
            logger.info(f"用户 {current_username} 更名为 {new_username}")
        
        # 更新密码
        new_password = data.get('password')
        if new_password:
            valid, msg = validate_password(new_password)
            if not valid:
                return jsonify({'success': False, 'message': msg}), 400
            
            if is_password_weak(new_password):
                return jsonify({'success': False, 'message': '密码过于简单，请使用更复杂的密码'}), 400
            
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256:600000')
            logger.info(f"用户 {user.username} 已更新密码")
        
        # 更新头像
        avatar = data.get('avatar')
        if avatar:
            if avatar.startswith('data:image'):
                logger.info(f"接收到Base64编码的头像数据")
                file_path = save_base64_image(avatar, user.username)
                if file_path:
                    user.avatar = file_path
                    logger.info(f"已保存用户 {user.username} 的头像")
                else:
                    return jsonify({'success': False, 'message': '头像保存失败'}), 500
            else:
                user.avatar = avatar
                logger.info(f"已更新用户 {user.username} 的头像URL")
        
        db.session.commit()
        logger.info(f"用户 {user.username} 信息更新成功")
        
        return jsonify({
            'success': True,
            'message': '用户信息更新成功',
            'data': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新用户信息失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '更新失败，请稍后重试'}), 500

# ==================== 密码重置功能 ====================

def send_password_reset_email():
    """发送密码重置邮件 - 增强版"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': '邮箱不能为空'}), 400
        
        if not validate_email(email):
            return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': '该邮箱未注册'}), 404
        
        # 生成重置令牌
        timestamp = str(int(datetime.utcnow().timestamp()))
        raw_token = f"{user.id}:{timestamp}:{user.email}:{generate_random_token()}"
        token = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 存储令牌
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=AuthConfig.RESET_TOKEN_EXPIRE_HOURS)
        db.session.commit()
        
        # 发送重置邮件
        reset_url = f"http://localhost:5000/reset-password?token={token}"
        msg = Message(
            subject='【学习平台】密码重置',
            sender='3444793531@qq.com',
            recipients=[email]
        )
        msg.body = f'''您好！

您收到了密码重置请求。

请点击以下链接重置密码（{AuthConfig.RESET_TOKEN_EXPIRE_HOURS}小时内有效）：
{reset_url}

如果您没有请求重置密码，请忽略此邮件。

---
学习平台
'''
        
        mail.send(msg)
        logger.info(f"密码重置邮件已发送到 {email}")
        
        return jsonify({
            'success': True,
            'message': '密码重置链接已发送到您的邮箱'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'密码重置邮件发送失败: {e}', exc_info=True)
        return jsonify({'success': False, 'message': '发送失败，请稍后重试'}), 500

def reset_password():
    """使用Token重置密码 - 增强版"""
    try:
        data = request.json
        token = data.get('token')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not token or not new_password:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400
        
        valid, msg = validate_password(new_password)
        if not valid:
            return jsonify({'success': False, 'message': msg}), 400
        
        if is_password_weak(new_password):
            return jsonify({'success': False, 'message': '密码过于简单，请使用更复杂的密码'}), 400
        
        # 查找并验证令牌
        user = User.query.filter_by(reset_token=token).first()
        if not user:
            return jsonify({'success': False, 'message': '无效的令牌'}), 400
        
        if user.reset_token_expiry < datetime.utcnow():
            return jsonify({'success': False, 'message': '令牌已过期，请重新申请'}), 400
        
        # 更新密码
        user.password = generate_password_hash(new_password, method='pbkdf2:sha256:600000')
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        logger.info(f"用户 {user.username} 密码重置成功")
        return jsonify({'success': True, 'message': '密码重置成功'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"密码重置失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '密码重置失败，请稍后重试'}), 500

def verify_token():
    """验证重置令牌是否有效"""
    try:
        data = request.json
        token = data.get('token')
        
        if not token:
            return jsonify({'success': False, 'message': '缺少令牌'}), 400
        
        user = User.query.filter_by(reset_token=token).first()
        if not user:
            return jsonify({'success': False, 'message': '无效的令牌'}), 400
        
        if user.reset_token_expiry < datetime.utcnow():
            return jsonify({'success': False, 'message': '令牌已过期'}), 400
        
        return jsonify({'success': True, 'message': '令牌有效'}), 200
        
    except Exception as e:
        logger.error(f"验证令牌失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '验证失败'}), 500

@jwt_required()
def change_password():
    """已登录用户修改密码 - 增强版"""
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
        
        if not check_password_hash(user.password, old_password):
            return jsonify({'success': False, 'message': '原密码错误'}), 400
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '两次输入的密码不一致'}), 400
        
        valid, msg = validate_password(new_password)
        if not valid:
            return jsonify({'success': False, 'message': msg}), 400
        
        if is_password_weak(new_password):
            return jsonify({'success': False, 'message': '密码过于简单，请使用更复杂的密码'}), 400
        
        user.password = generate_password_hash(new_password, method='pbkdf2:sha256:600000')
        db.session.commit()
        
        logger.info(f"用户 {user.username} 密码修改成功")
        return jsonify({'success': True, 'message': '密码修改成功'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"修改密码失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '修改密码失败，请稍后重试'}), 500