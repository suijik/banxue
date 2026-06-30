from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Mistake, User, PracticeQuestion
from extension import db
from datetime import datetime
import os
import traceback
import hashlib
from utils import extract_mistakes_with_vision, normalize_math_text, simplify_question_no, question_text_needs_refinement, merge_refined_mistakes, image_file_to_data_url, build_display_question


def sanitize_mistake_payload(data):
    if not isinstance(data, dict):
        return data

    cleaned = dict(data)
    for field in ['stem_summary', 'question', 'user_answer', 'correct_answer', 'explanation']:
        cleaned[field] = normalize_math_text(cleaned.get(field))
    cleaned['question_no'] = simplify_question_no(cleaned.get('question_no'))
    return cleaned


def build_exam_group_key(data):
    if not isinstance(data, dict):
        return ''

    exam_analysis_id = data.get('exam_analysis_id')
    if exam_analysis_id:
        return f"analysis-{exam_analysis_id}"

    subject = normalize_math_text(data.get('subject')) or '未知科目'
    exam_name = normalize_math_text(data.get('exam_name')) or '未命名试卷'
    exam_image_path = normalize_math_text(data.get('exam_image_path'))
    created_at = normalize_math_text(data.get('created_at'))
    created_date = created_at[:10] if created_at else ''
    raw_key = f"{subject}|{exam_name}|{exam_image_path}|{created_date}"
    digest = hashlib.md5(raw_key.encode('utf-8')).hexdigest()[:16]
    return f"snapshot-{digest}"


def resolve_exam_image_file_path(image_path):
    if not image_path:
        return None
    if os.path.isabs(image_path) and os.path.exists(image_path):
        return image_path

    normalized = image_path.replace('/', os.sep).lstrip(os.sep)
    candidate = os.path.join(current_app.root_path, normalized)
    if os.path.exists(candidate):
        return candidate

    if normalized.startswith(f"static{os.sep}"):
        candidate = os.path.join(current_app.root_path, normalized)
        if os.path.exists(candidate):
            return candidate

    return None


def repair_incomplete_mistakes(mistakes):
    groups = {}
    for mistake in mistakes:
        if not question_text_needs_refinement(mistake.question, mistake.stem_summary):
            continue

        image_path = mistake.exam_image_path_snapshot
        if not image_path and mistake.exam_analysis:
            image_path = mistake.exam_analysis.exam_image_path

        group_key = (mistake.exam_analysis_id or mistake.id, image_path, mistake.subject)
        groups.setdefault(group_key, []).append(mistake)

    has_updates = False
    for (_, image_path, subject), group_mistakes in groups.items():
        file_path = resolve_exam_image_file_path(image_path)
        if not file_path:
            continue

        try:
            image_data = image_file_to_data_url(file_path)
            refined_mistakes, error = extract_mistakes_with_vision(
                image_data,
                subject or '未知科目',
                [
                    {
                        'question_no': mistake.question_no,
                        'stem_summary': mistake.stem_summary,
                        'error_text': mistake.explanation
                    }
                    for mistake in group_mistakes
                ]
            )
            if error or not refined_mistakes:
                continue

            merged = merge_refined_mistakes(
                [
                    {
                        'question_no': mistake.question_no,
                        'stem_summary': mistake.stem_summary,
                        'question_text': mistake.question,
                        'user_answer': mistake.user_answer,
                        'correct_answer': mistake.correct_answer,
                        'explanation': mistake.explanation
                    }
                    for mistake in group_mistakes
                ],
                refined_mistakes
            )

            for mistake, merged_item in zip(group_mistakes, merged):
                new_question_text = normalize_math_text(merged_item.get('question_text'))
                if new_question_text and should_update_question(mistake.question, new_question_text, mistake.stem_summary):
                    mistake.question = build_display_question(mistake.question_no or '未知题号', new_question_text)
                    has_updates = True
                for field in ['user_answer', 'correct_answer', 'explanation']:
                    current_value = normalize_math_text(getattr(mistake, field))
                    new_value = normalize_math_text(merged_item.get(field))
                    if new_value and len(new_value) > len(current_value):
                        setattr(mistake, field, new_value)
                        has_updates = True
        except Exception as e:
            print(f"错题懒修复失败: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")

    if has_updates:
        db.session.commit()


def should_update_question(current_question, refined_question, stem_summary):
    current = normalize_math_text(current_question)
    refined = normalize_math_text(refined_question)
    if not refined:
        return False
    if question_text_needs_refinement(current, stem_summary) and not question_text_needs_refinement(refined, stem_summary):
        return True
    if len(refined) >= len(current) + 8:
        return True
    return False

@jwt_required()
def get_mistakes():
    """获取用户的错题列表"""
    try:
        print("=== 开始获取错题列表 ===")
        user_id = get_jwt_identity()

        print(f"当前用户ID: {user_id}")

        # 获取查询参数
        subject = request.args.get('subject')
        is_mastered = request.args.get('is_mastered')
        print(f"查询参数 - subject: {subject}, is_mastered: {is_mastered}")
        
        # 构建查询
        query = Mistake.query.filter_by(user_id=user_id)
        
        if subject:
            query = query.filter_by(subject=subject)
        if is_mastered is not None:
            # 将字符串转换为布尔值
            is_mastered_bool = is_mastered.lower() == 'true'
            query = query.filter_by(is_mastered=is_mastered_bool)
        
        group_by_exam = request.args.get('group_by_exam', 'false').lower() == 'true'

        # 执行查询
        mistakes = query.order_by(Mistake.created_at.desc()).all()
        print(f"查询到 {len(mistakes)} 条错题记录")

        # 错题本列表接口应尽量轻量，避免每次打开页面都触发原卷重读和视觉模型二次修复。
        # 如需修复题干，应在入库阶段或详情页按需处理，而不是阻塞列表加载。

        if group_by_exam:
            grouped = {}
            for mistake in mistakes:
                data = sanitize_mistake_payload(mistake.to_dict())
                group_key = build_exam_group_key(data)
                if group_key not in grouped:
                    grouped[group_key] = {
                        'group_id': group_key,
                        'exam_analysis_id': data.get('exam_analysis_id'),
                        'exam_name': data.get('exam_name') or '未命名试卷',
                        'exam_image_path': data.get('exam_image_path'),
                        'subject': data.get('subject') or '未知科目',
                        'mistake_count': 0,
                        'latest_created_at': data.get('created_at'),
                        'mistakes': []
                    }

                grouped[group_key]['mistakes'].append(data)
                grouped[group_key]['mistake_count'] += 1
                if data.get('created_at') and data.get('created_at') > grouped[group_key]['latest_created_at']:
                    grouped[group_key]['latest_created_at'] = data.get('created_at')
                if data.get('subject') and grouped[group_key]['subject'] == '未知科目':
                    grouped[group_key]['subject'] = data.get('subject')

            grouped_list = sorted(
                grouped.values(),
                key=lambda item: item.get('latest_created_at') or '',
                reverse=True
            )
            return jsonify({
                'success': True,
                'data': grouped_list
            })
        
        return jsonify({
            'success': True,
            'data': [sanitize_mistake_payload(mistake.to_dict()) for mistake in mistakes]
        })
        
    except Exception as e:
        print(f"获取错题列表失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'获取错题列表失败: {str(e)}'
        }), 500

@jwt_required()
def create_mistake():
    """创建新的错题记录"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    mistake = Mistake(
        user_id=user_id,
        subject=data['subject'],
        question=data['question'],
        user_answer=data.get('user_answer'),
        correct_answer=data['correct_answer'],
        explanation=data.get('explanation')
    )
    
    db.session.add(mistake)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '创建错题成功',
        'data': mistake.to_dict()
    }), 201

@jwt_required()
def update_mistake(mistake_id):
    """更新错题记录"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            print("错误：请求体为空")
            return jsonify({'success': False, 'message': '请求体不能为空'}), 400

        # 从JWT获取用户ID
        user_id = get_jwt_identity()
        print(f"更新错题请求: 错题ID={mistake_id}, 用户ID={user_id}")

        # 查找错题记录
        mistake = Mistake.query.filter_by(id=mistake_id).first()
        if not mistake:
            print(f"错误：错题不存在: ID={mistake_id}")
            return jsonify({
                'success': False,
                'message': '错题不存在'
            }), 404

        # 验证错题所属的用户
        if mistake.user_id != user_id:
            print(f"权限错误: 错题所属用户ID={mistake.user_id}, 请求用户ID={user_id}")
            return jsonify({
                'success': False,
                'message': '没有权限修改此错题'
            }), 403
        
        # 更新字段
        if 'subject' in data:
            mistake.subject = data['subject']
        if 'question' in data:
            mistake.question = data['question']
        if 'user_answer' in data:
            mistake.user_answer = data['user_answer']
        if 'correct_answer' in data:
            mistake.correct_answer = data['correct_answer']
        if 'explanation' in data:
            mistake.explanation = data['explanation']
        if 'error_type' in data:
            mistake.error_type = data['error_type']
        if 'is_mastered' in data:
            # 确保is_mastered是布尔值
            is_mastered = data['is_mastered']
            if isinstance(is_mastered, str):
                is_mastered = is_mastered.lower() == 'true'
            mistake.is_mastered = bool(is_mastered)
            print(f"设置is_mastered={mistake.is_mastered}")
        
        db.session.commit()
        print(f"错题更新成功: ID={mistake_id}")
        return jsonify({
            'success': True,
            'message': '更新错题成功',
            'data': mistake.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        print(f"更新错题失败: {error_msg}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'更新错题失败: {error_msg}'
        }), 500

@jwt_required()
def delete_mistake(mistake_id):
    """删除错题记录"""
    user_id = get_jwt_identity()
    mistake = Mistake.query.filter_by(id=mistake_id, user_id=user_id).first_or_404()
    
    db.session.delete(mistake)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '删除错题成功'
    }), 200


@jwt_required()
def delete_mistake_group():
    """按试卷分组删除整组错题"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求体不能为空'}), 400

        group_id = data.get('group_id')
        if not group_id:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400

        user_id = get_jwt_identity()

        mistakes = Mistake.query.filter_by(user_id=user_id).all()
        target_mistakes = []
        for mistake in mistakes:
            mistake_data = sanitize_mistake_payload(mistake.to_dict())
            if build_exam_group_key(mistake_data) == group_id:
                target_mistakes.append(mistake)

        if not target_mistakes:
            return jsonify({'success': False, 'message': '未找到对应试卷错题'}), 404

        deleted_count = len(target_mistakes)
        for mistake in target_mistakes:
            db.session.delete(mistake)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': '整张试卷错题已删除',
            'data': {
                'deleted_count': deleted_count,
                'group_id': group_id
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"删除整组错题失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'删除整组错题失败: {str(e)}'
        }), 500

@jwt_required()
def get_practice_questions():
    """获取练习题列表"""
    try:
        user_id = get_jwt_identity()

        # 获取查询参数
        subject = request.args.get('subject')

        # 构建查询
        query = PracticeQuestion.query.filter_by(user_id=user_id)
        if subject:
            query = query.filter_by(subject=subject)
        
        # 执行查询
        questions = query.order_by(PracticeQuestion.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [q.to_dict() for q in questions]
        })
        
    except Exception as e:
        print(f"获取练习题列表失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'获取练习题列表失败: {str(e)}'
        }), 500

@jwt_required()
def update_practice_question(question_id):
    """更新练习题掌握状态"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            print("错误：请求体为空")
            return jsonify({'success': False, 'message': '请求体不能为空'}), 400

        # 从JWT获取用户ID
        user_id = get_jwt_identity()
        print(f"更新练习题请求: 题目ID={question_id}, 用户ID={user_id}")

        # 查找练习题记录
        question = PracticeQuestion.query.filter_by(id=question_id).first()
        if not question:
            print(f"错误：练习题不存在: ID={question_id}")
            return jsonify({
                'success': False,
                'message': '练习题不存在'
            }), 404
            
        # 验证练习题所属的用户
        if question.user_id != user_id:
            print(f"权限错误: 练习题所属用户ID={question.user_id}, 请求用户ID={user_id}")
            return jsonify({
                'success': False,
                'message': '没有权限修改此练习题'
            }), 403
        
        # 更新掌握状态
        if 'is_mastered' in data:
            # 确保is_mastered是布尔值
            is_mastered = data['is_mastered']
            if isinstance(is_mastered, str):
                is_mastered = is_mastered.lower() == 'true'
            question.is_mastered = bool(is_mastered)
            print(f"设置练习题is_mastered={question.is_mastered}")
        
        db.session.commit()
        print(f"练习题更新成功: ID={question_id}")
        return jsonify({
            'success': True,
            'message': '更新练习题成功',
            'data': question.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        print(f"更新练习题失败: {error_msg}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'更新练习题失败: {error_msg}'
        }), 500

@jwt_required()
def delete_practice_question(question_id):
    """删除练习题"""
    try:
        user_id = get_jwt_identity()

        # 查找练习题记录
        question = PracticeQuestion.query.filter_by(id=question_id).first()
        if not question:
            return jsonify({'success': False, 'message': '练习题不存在'}), 404

        # 验证权限
        if question.user_id != user_id:
            return jsonify({'success': False, 'message': '没有权限修改此练习题'}), 403
            
        db.session.delete(question)
        db.session.commit()
        print(f"成功删除练习题 ID: {question_id}")
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        db.session.rollback()
        print(f"删除练习题失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除练习题失败: {str(e)}'
        }), 500

