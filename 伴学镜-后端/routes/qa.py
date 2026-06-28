from flask import Blueprint, request, jsonify, session
from extension import zhipu_client, db
from models import User, ChatHistory
from datetime import datetime, timedelta
import logging
import json
import hashlib
from functools import lru_cache
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

qa_bp = Blueprint('qa', __name__)

# ==================== 配置常量 ====================
class QaConfig:
    """QA模块配置"""
    MAX_MESSAGES = 20  # 最多保留的消息条数
    MAX_CONTEXT_DAYS = 7  # 最多保留多少天的上下文
    MAX_HISTORY_PER_USER = 100  # 每个用户最多存储的历史记录
    SYSTEM_PROMPT = {
        "role": "system",
        "content": """你是家庭辅助智能教育平台里的AI老师"小伴"。你的任务是为学生提供学习方面的启发答疑。

【严格约束】：
1. 只能回答和学习、学科（数学、语文、英语、物理、化学等）、教育相关的问题。
2. 如果用户问了和学习无关的问题（比如游戏、娱乐、闲聊等），你必须委婉地拒绝，并引导他们回到学习上。
3. 你的回答应该具有启发性，不要直接给出最终答案，而是通过提问、给出思路等方式引导学生自己思考。
4. 语气要亲切、鼓励，像一个耐心辅导老师一样。
5. 回答要简洁明了，控制在200字以内。"""
    }
    
    # 模型配置
    TEXT_MODEL = "glm-4"
    VISION_MODEL = "glm-4v-plus"
    
    # 限制配置
    MAX_MESSAGE_LENGTH = 2000  # 单条消息最大长度
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 图片最大5MB

# ==================== 辅助函数 ====================

def truncate_message(content: str, max_length: int = QaConfig.MAX_MESSAGE_LENGTH) -> str:
    """截断过长的消息"""
    if len(content) > max_length:
        return content[:max_length] + "...(已截断)"
    return content

def is_learning_related(text: str) -> bool:
    """快速判断是否与学习相关（关键词过滤）"""
    learning_keywords = [
        '数学', '语文', '英语', '物理', '化学', '生物', '历史', '地理',
        '政治', '科学', '编程', '算法', '代码', '习题', '考试', '作业',
        '学习', '知识', '公式', '定理', '解题', '计算', '作文', '阅读',
        '单词', '语法', '方程', '函数', '几何', '代数', '实验'
    ]
    
    text_lower = text.lower()
    # 判断是否包含至少一个学习关键词
    has_keyword = any(keyword in text_lower for keyword in learning_keywords)
    
    # 如果是纯闲聊关键词，拒绝
    casual_keywords = ['游戏', '娱乐', '搞笑', '八卦', '明星', '电影', '音乐']
    is_casual = any(keyword in text_lower for keyword in casual_keywords)
    
    # 如果包含闲聊关键词且不包含学习关键词，视为非学习内容
    if is_casual and not has_keyword:
        return False
    
    return True

def build_conversation_context(history: List[Dict]) -> List[Dict]:
    """构建对话上下文"""
    # 从最近的对话中提取，确保不超过最大消息数
    messages = []
    
    # 添加系统提示
    messages.append(QaConfig.SYSTEM_PROMPT)
    
    # 提取历史消息（最近N条）
    recent_history = history[-QaConfig.MAX_MESSAGES:] if history else []
    
    for msg in recent_history:
        # 验证消息格式
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            # 确保消息角色正确
            role = msg.get('role')
            if role in ['user', 'assistant']:
                content = msg.get('content', '')
                # 截断过长内容
                if isinstance(content, str):
                    content = truncate_message(content)
                    messages.append({
                        'role': role,
                        'content': content
                    })
                elif isinstance(content, list):
                    # 处理多模态消息
                    messages.append(msg)
    
    return messages

def compress_history(history: List[Dict]) -> List[Dict]:
    """压缩历史记录 - 合并相似消息"""
    if not history:
        return []
    
    compressed = []
    current = None
    
    for msg in history:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            role = msg['role']
            content = msg['content']
            
            # 对于文本消息，可以尝试合并
            if isinstance(content, str) and current and current['role'] == role:
                # 如果角色相同，合并内容
                if len(current['content']) + len(content) < 500:
                    current['content'] += "\n" + content
                    continue
            
            # 否则添加新消息
            current = msg.copy()
            compressed.append(current)
    
    return compressed

def save_chat_history(user_id: int, messages: List[Dict]) -> bool:
    """保存聊天历史到数据库"""
    try:
        # 获取或创建用户的历史记录
        chat_history = ChatHistory.query.filter_by(user_id=user_id).first()
        
        if chat_history:
            # 更新现有记录
            history = json.loads(chat_history.messages) if chat_history.messages else []
            
            # 添加新消息
            history.extend(messages)
            
            # 限制存储数量
            if len(history) > QaConfig.MAX_HISTORY_PER_USER:
                history = history[-QaConfig.MAX_HISTORY_PER_USER:]
            
            chat_history.messages = json.dumps(history)
            chat_history.updated_at = datetime.utcnow()
        else:
            # 创建新记录
            chat_history = ChatHistory(
                user_id=user_id,
                messages=json.dumps(messages),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(chat_history)
        
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"保存聊天历史失败: {e}")
        db.session.rollback()
        return False

def get_chat_history(user_id: int, limit: int = QaConfig.MAX_MESSAGES) -> List[Dict]:
    """获取用户聊天历史"""
    try:
        chat_history = ChatHistory.query.filter_by(user_id=user_id).first()
        if chat_history and chat_history.messages:
            history = json.loads(chat_history.messages)
            # 返回最近N条
            return history[-limit:] if history else []
        return []
    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        return []

def get_session_context(username: str) -> List[Dict]:
    """获取会话上下文（基于内存或数据库）"""
    # 优先从数据库获取
    user = User.query.filter_by(username=username).first()
    if user:
        return get_chat_history(user.id)
    return []

def update_session_context(username: str, new_messages: List[Dict]):
    """更新会话上下文"""
    user = User.query.filter_by(username=username).first()
    if user:
        save_chat_history(user.id, new_messages)

# ==================== 缓存装饰器 ====================

def cache_response(max_size=128):
    """缓存AI响应的装饰器"""
    cache = {}
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存key
            data = kwargs.get('data') or args[0] if args else None
            if not data:
                return func(*args, **kwargs)
            
            # 提取关键信息作为缓存键
            cache_key = hashlib.md5(
                f"{data.get('username')}:{data.get('messages', [])[-1:]}".encode()
            ).hexdigest()
            
            # 检查缓存
            if cache_key in cache:
                cached_time, cached_response = cache[cache_key]
                # 如果缓存时间在5分钟内，直接返回
                if (datetime.utcnow() - cached_time).seconds < 300:
                    logger.info(f"返回缓存响应: {cache_key[:10]}")
                    return cached_response
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存储缓存
            cache[cache_key] = (datetime.utcnow(), result)
            
            # 限制缓存大小
            if len(cache) > max_size:
                # 删除最旧的缓存项
                oldest_key = min(cache.keys(), key=lambda k: cache[k][0])
                del cache[oldest_key]
            
            return result
        return wrapper
    return decorator

# ==================== 核心API ====================

@qa_bp.route('/chat', methods=['POST'])
def chat():
    """
    处理小伴的聊天请求 - 优化版
    """
    try:
        data = request.json
        username = data.get('username')
        messages = data.get('messages', [])
        image_base64 = data.get('image_base64')
        
        # 验证输入
        if not messages:
            return jsonify({'success': False, 'message': '消息不能为空'}), 400
        
        # 获取最后一条消息
        last_message = messages[-1] if messages else {}
        user_message = last_message.get('content', '')
        
        # 截断过长的消息
        if isinstance(user_message, str):
            user_message = truncate_message(user_message)
        
        # 检查是否与学习相关（快速过滤）
        if isinstance(user_message, str) and not is_learning_related(user_message):
            return jsonify({
                'success': True,
                'data': {
                    'reply': '小伴主要是你的学习助手哦，我们还是来讨论学习上的问题吧！有什么学科知识需要我帮忙吗？'
                }
            })
        
        # 获取用户信息
        user = None
        if username:
            user = User.query.filter_by(username=username).first()
            if not user:
                logger.warning(f"用户 {username} 不存在，使用匿名模式")
        
        # 获取历史上下文
        historical_context = []
        if user:
            # 从数据库获取最近的历史记录
            historical_context = get_chat_history(user.id)
            logger.info(f"加载用户 {username} 的历史记录: {len(historical_context)} 条")
        
        # 构建发送给AI的消息
        api_messages = []
        
        # 添加系统提示
        api_messages.append(QaConfig.SYSTEM_PROMPT)
        
        # 添加历史上下文（最近N条）
        if historical_context:
            # 压缩历史
            compressed_history = compress_history(historical_context)
            # 限制消息数量
            context_messages = compressed_history[-QaConfig.MAX_MESSAGES:]
            
            for msg in context_messages:
                if isinstance(msg, dict) and 'role' in msg:
                    api_messages.append(msg)
        
        # 处理新的消息
        if image_base64:
            # 处理图片消息
            # 验证图片大小
            image_size = len(image_base64) * 3 / 4  # base64解码后大小
            if image_size > QaConfig.MAX_IMAGE_SIZE:
                return jsonify({
                    'success': False,
                    'message': '图片过大，请压缩后上传（最大5MB）'
                }), 400
            
            # 构建多模态消息
            image_url = image_base64 if image_base64.startswith('data:image') else f"data:image/jpeg;base64,{image_base64}"
            
            # 限制图片URL长度
            if len(image_url) > 10000:
                return jsonify({
                    'success': False,
                    'message': '图片数据过大，请压缩后重试'
                }), 400
            
            # 构建用户消息（多模态）
            user_content = []
            if user_message:
                user_content.append({
                    "type": "text",
                    "text": user_message
                })
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            })
            
            api_messages.append({
                "role": "user",
                "content": user_content
            })
            
            model_name = QaConfig.VISION_MODEL
        else:
            # 普通文本消息
            # 确保消息格式正确
            if last_message.get('role') == 'user':
                api_messages.append({
                    "role": "user",
                    "content": user_message
                })
            else:
                # 如果前端消息格式不规范，自动修正
                api_messages.append({
                    "role": "user",
                    "content": user_message
                })
            
            model_name = QaConfig.TEXT_MODEL
        
        # 确保不超过最大消息数
        if len(api_messages) > QaConfig.MAX_MESSAGES + 1:  # +1 包含系统提示
            # 保留系统提示和最新的消息
            api_messages = [api_messages[0]] + api_messages[-(QaConfig.MAX_MESSAGES):]
        
        # 日志记录
        logger.info(f"发送给AI的消息数: {len(api_messages)} (模型: {model_name})")
        
        # 调用AI API
        try:
            # 设置超时
            response = zhipu_client.chat.completions.create(
                model=model_name,
                messages=api_messages,
                temperature=0.7,
                max_tokens=500,
                timeout=30  # 30秒超时
            )
            
            reply_text = response.choices[0].message.content
            
            # 截断过长的回复
            if len(reply_text) > 500:
                reply_text = reply_text[:500] + "..."
            
            # 保存历史记录
            if user:
                # 保存用户消息和AI回复
                new_messages = [
                    {
                        "role": "user",
                        "content": user_message,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "role": "assistant",
                        "content": reply_text,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
                save_chat_history(user.id, new_messages)
                logger.info(f"保存用户 {username} 的聊天历史")
            
            return jsonify({
                'success': True,
                'data': {
                    'reply': reply_text,
                    'context_used': len(historical_context) if historical_context else 0
                }
            })
            
        except TimeoutError:
            logger.error("AI API 请求超时")
            return jsonify({
                'success': False,
                'message': 'AI服务响应超时，请稍后重试'
            }), 504
        except Exception as e:
            logger.error(f"AI API 调用失败: {e}")
            return jsonify({
                'success': False,
                'message': 'AI服务器繁忙，请稍后再试'
            }), 500
            
    except Exception as e:
        logger.error(f"聊天处理失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'处理失败: {str(e)}'
        }), 500


@qa_bp.route('/history/<username>', methods=['GET'])
def get_chat_history_api(username):
    """获取用户的聊天历史"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        limit = min(int(request.args.get('limit', 50)), 100)  # 最多100条
        
        history = get_chat_history(user.id, limit)
        
        return jsonify({
            'success': True,
            'data': {
                'history': history,
                'count': len(history)
            }
        })
    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@qa_bp.route('/history/<username>', methods=['DELETE'])
def clear_chat_history(username):
    """清空用户的聊天历史"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        chat_history = ChatHistory.query.filter_by(user_id=user.id).first()
        if chat_history:
            chat_history.messages = json.dumps([])
            chat_history.updated_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"清空用户 {username} 的聊天历史")
        
        return jsonify({
            'success': True,
            'message': '聊天历史已清空'
        })
    except Exception as e:
        logger.error(f"清空聊天历史失败: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@qa_bp.route('/suggestions', methods=['POST'])
def get_quick_suggestions():
    """获取快速建议问题"""
    suggestions = [
        "如何提高数学解题能力？",
        "英语语法学习有什么技巧？",
        "物理题目的解题思路是什么？",
        "怎样写好一篇作文？",
        "化学方程式怎么记忆？"
    ]
    return jsonify({
        'success': True,
        'data': {
            'suggestions': suggestions
        }
    })


@qa_bp.route('/stats/<username>', methods=['GET'])
def get_chat_stats(username):
    """获取聊天统计信息"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        history = get_chat_history(user.id)
        
        # 统计数据
        total_messages = len(history)
        user_messages = sum(1 for msg in history if msg.get('role') == 'user')
        assistant_messages = sum(1 for msg in history if msg.get('role') == 'assistant')
        
        # 计算平均消息长度
        avg_length = 0
        if total_messages > 0:
            total_length = sum(len(str(msg.get('content', ''))) for msg in history)
            avg_length = total_length // total_messages
        
        return jsonify({
            'success': True,
            'data': {
                'total_messages': total_messages,
                'user_messages': user_messages,
                'assistant_messages': assistant_messages,
                'avg_message_length': avg_length,
                'history_limit': QaConfig.MAX_HISTORY_PER_USER
            }
        })
    except Exception as e:
        logger.error(f"获取聊天统计失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500