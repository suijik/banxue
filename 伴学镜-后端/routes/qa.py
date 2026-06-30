from flask import Blueprint, jsonify, request
from models import db, User
from utils import zhipu_client
import json

qa_bp = Blueprint('qa', __name__)

@qa_bp.route('/chat', methods=['POST'])
def chat():
    """
    处理小伴的聊天请求
    """
    data = request.json
    username = data.get('username')
    messages = data.get('messages', [])
    image_base64 = data.get('image_base64')
    
    if not messages:
        return jsonify({'success': False, 'message': '消息不能为空'}), 400
        
    system_prompt = {
        "role": "system",
        "content": "你是家庭辅助智能教育平台里的AI老师“小伴”。你的任务是为学生提供学习方面的启发答疑。\n"
                   "【严格约束】：\n"
                   "1. 只能回答和学习、学科（数学、语文、英语、物理、化学等）、教育相关的问题。\n"
                   "2. 如果用户问了和学习无关的问题（比如游戏、娱乐、闲聊等），你必须委婉地拒绝，并引导他们回到学习上。例如：“小伴主要是你的学习助手哦，我们还是来讨论学习上的问题吧！”\n"
                   "3. 你的回答应该具有启发性，不要直接给出最终答案，而是通过提问、给出思路等方式引导学生自己思考。\n"
                   "4. 语气要亲切、鼓励，像一个耐心辅导老师一样。"
    }
    
    api_messages = [system_prompt]
    
    if image_base64:
        for msg in messages[:-1]:
            api_messages.append(msg)
            
        last_msg = messages[-1]
        image_url = image_base64 if image_base64.startswith('data:image') else f"data:image/jpeg;base64,{image_base64}"
        
        api_messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": last_msg.get("content", "")
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }
            ]
        })
        
        model_name = "glm-4v-plus"
    else:
        api_messages.extend(messages)
        model_name = "glm-4"
        
    try:
        response = zhipu_client.chat.completions.create(
            model=model_name,
            messages=api_messages
        )
        
        reply_text = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'data': {
                'reply': reply_text
            }
        })
    except Exception as e:
        print(f"小伴答疑报错: {str(e)}")
        return jsonify({'success': False, 'message': 'AI服务器繁忙，请稍后再试'}), 500