from flask import request, jsonify, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import re
import random
import string
import os
from datetime import datetime
from extension import db, mail
from models import User, ExamAnalysis, Mistake, PracticeQuestion

# 存储验证码的字典（key: 邮箱, value: 验证码）
verification_codes = {}


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

    # 验证码校验
    if email not in verification_codes or verification_codes[email] != code:
        return jsonify({'success': False, 'message': '验证码错误或已过期'}), 400

    # 检查用户名和邮箱是否已存在
    with current_app.app_context():
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': '用户名已存在'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': '邮箱已存在'}), 400

        # 创建新用户
        try:
            new_user = User(
                username=data['username'],
                email=data['email'],
                password=data['password']  # 实际使用时需要加密处理
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
    with current_app.app_context():
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            print(f"用户 {username} 登录成功")
            
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
            print(f"用户 {username} 登录失败：用户名或密码错误")
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
        print(f"获取用户信息失败: {e}")
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
    print(email)

    # 生成验证码
    code = generate_verification_code()
    verification_codes[email] = code  # 存储验证码
    print(verification_codes[email])
    print(code)

    # 发送验证码邮件
    msg = Message(
        subject='验证码',  # 邮件主题
        sender='3444793531@qq.com',  # 发件人邮箱（与配置中的 MAIL_USERNAME 一致）
        recipients=[email]  # 收件人邮箱
    )
    print(f'发送验证码到邮箱：{email}')
    msg.body = f'您的验证码是：{code}，请在5分钟内使用。'  # 邮件内容

    try:
        mail.send(msg)  # 发送邮件
        return jsonify({'success': True, 'message': '验证码已发送'}), 200
    except Exception as e:
        print(f'邮件发送失败: {e}')
        return jsonify({'success': False, 'message': '邮件发送失败，请检查邮箱配置'}), 500

def update_userinfo():
    """更新用户信息（用户名、头像和密码）"""
    print("收到更新用户信息的请求")
    data = request.json
    
    # 将头像数据从日志输出中排除，避免日志过大
    log_data = {k: v if k != 'avatar' else '[头像数据已省略]' for k, v in data.items()}
    print(f"接收到的数据: {log_data}")
    
    # 需要的字段：username（确定用户），password（可选），avatar（可选）
    username = data.get('username')
    if not username:
        print("错误：用户名不能为空")
        return jsonify({'success': False, 'message': '用户名不能为空'}), 400
    
    try:
        # 先根据session或其他方式获取当前登录用户
        current_username = username  # 这里假设前端传过来的就是当前登录用户
        user = User.query.filter_by(username=current_username).first()
        
        if not user:
            print(f"错误：找不到用户 {current_username}")
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 更新用户名
        new_username = data.get('username')
        if new_username and new_username != current_username:
            # 检查新用户名是否已存在
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user.id:
                print(f"错误：用户名 {new_username} 已被使用")
                return jsonify({'success': False, 'message': '该用户名已被使用'}), 400
            
            user.username = new_username
            print(f"已更新用户名从 {current_username} 到 {new_username}")
        
        # 更新密码（如果提供）
        new_password = data.get('password')
        if new_password:
            if len(new_password) < 8:
                print("错误：密码长度不足")
                return jsonify({'success': False, 'message': '密码至少8位'}), 400
            user.password = new_password
            print(f"已更新用户 {username} 的密码")
        
        # 更新头像（如果提供）
        avatar = data.get('avatar')
        if avatar:
            # 检查是否是Base64数据
            if avatar.startswith('data:image'):
                print(f"接收到Base64编码的头像数据，长度: {len(avatar)} 字符")
                
                # 转换为URL路径存储
                file_path = save_base64_image(avatar, username)
                if file_path:
                    user.avatar = file_path
                    print(f"已保存用户 {username} 的头像到文件: {file_path}")
                else:
                    print(f"头像保存失败")
                    return jsonify({'success': False, 'message': '头像保存失败'}), 500
            else:
                print(f"接收到头像URL，长度: {len(avatar)} 字符")
                user.avatar = avatar
                print(f"已更新用户 {username} 的头像URL")
        
        db.session.commit()
        print(f"成功更新用户 {username} 的信息")
        return jsonify({
            'success': True, 
            'message': '用户信息更新成功',
            'data': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        error_message = str(e)
        print(f"更新用户信息失败: {error_message}")
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
        print(f"保存图片失败: {e}")
        return None
