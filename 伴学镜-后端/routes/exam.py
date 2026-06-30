from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import time
import base64
from werkzeug.utils import secure_filename
from extension import db
from models import User, ExamAnalysis, Mistake
from utils import save_base64_image as save_exam_image, analyze_exam_paper_with_vision, extract_mistakes_with_vision, build_exam_marks, build_display_question, normalize_math_text, simplify_question_no, question_text_needs_refinement, merge_refined_mistakes, generate_followup_practice_questions, save_followup_practice_questions, detect_supported_learning_material_with_vision, UNSUPPORTED_EXAM_UPLOAD_MESSAGE
import traceback
import threading
from flask import Flask


def sanitize_exam_analysis_payload(data):
    if not isinstance(data, dict):
        return data

    cleaned = dict(data)
    marks = []
    for mark in cleaned.get('marks', []) or []:
        if not isinstance(mark, dict):
            continue
        marks.append({
            **mark,
            'question_no': simplify_question_no(mark.get('question_no')),
            'stem_summary': normalize_math_text(mark.get('stem_summary')),
            'error_text': normalize_math_text(mark.get('error_text')),
            'correct_answer': normalize_math_text(mark.get('correct_answer')),
            'thinking_hint': normalize_math_text(mark.get('thinking_hint'))
        })
    cleaned['marks'] = marks
    return cleaned

@jwt_required()
def upload_exam_paper():
    """上传试卷图片并进行分析"""
    try:
        print("开始处理试卷上传请求")
        data = request.get_json()
        if not data:
            print("错误：请求体为空")
            return jsonify({'success': False, 'message': '请求体不能为空'}), 400

        # 检查请求参数的键名
        print(f"请求参数键名: {list(data.keys())}")

        # 验证必要参数，兼容两种可能的键名
        required_fields = [('imageData', 'image')]
        missing_fields = []
        for field in required_fields:
            if isinstance(field, tuple):
                # 如果是元组，检查是否至少有一个键存在
                if not any(k in data for k in field):
                    missing_fields.append(' 或 '.join(field))
            elif field not in data:
                missing_fields.append(field)

        if missing_fields:
            print(f"错误：缺少必要参数: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f'缺少必要参数: {", ".join(missing_fields)}'
            }), 400

        # 从JWT获取用户
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            print(f"错误：用户 ID={user_id} 不存在")
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        username = user.username

        # 获取图片数据，兼容两种可能的键名
        image_data = data.get('imageData') or data.get('image')

        print(f"接收到用户 {username} 的试卷上传请求")

        # 验证图片数据格式
        if not isinstance(image_data, str) or not image_data.startswith('data:image'):
            print("错误：图片数据格式不正确")
            return jsonify({
                'success': False,
                'message': '图片数据格式不正确，必须是Base64编码的图片数据'
            }), 400

        print("开始进行上传内容前置识别")
        support_result, support_error = detect_supported_learning_material_with_vision(
            image_data,
            data.get('examName', '')
        )
        if support_error:
            print(f"上传内容前置识别失败: {support_error}")
            return jsonify({
                'success': False,
                'message': '图片内容识别失败，请稍后重试'
            }), 500

        if not support_result.get('is_learning_material'):
            print(f"上传内容识别为非可批改学习材料: {support_result}")
            return jsonify({
                'success': False,
                'message': UNSUPPORTED_EXAM_UPLOAD_MESSAGE,
                'code': 'UNSUPPORTED_EXAM_IMAGE',
                'data': support_result
            }), 400
            
        # 保存图片
        try:
            print("开始保存试卷图片")
            image_path = save_exam_image(image_data, username)
            if not image_path:
                print("错误：保存图片失败")
                return jsonify({'success': False, 'message': '保存图片失败'}), 500
            print(f"图片保存成功，路径: {image_path}")
        except Exception as e:
            print(f"保存图片时发生错误: {str(e)}")
            return jsonify({'success': False, 'message': f'保存图片失败: {str(e)}'}), 500
            
        # 创建试卷分析记录
        try:
            print("创建试卷分析记录")
            # 获取试卷名称（如果有）
            exam_name = data.get('examName', f"{username}的试卷")
            exam_analysis = ExamAnalysis(
                user_id=user.id,
                exam_image_path=image_path,
                status='pending',
                exam_name=exam_name
            )
            db.session.add(exam_analysis)
            db.session.commit()
            print(f"创建分析记录成功，ID: {exam_analysis.id}")
        except Exception as e:
            print(f"创建分析记录失败: {str(e)}")
            return jsonify({'success': False, 'message': f'创建分析记录失败: {str(e)}'}), 500
        
        # 在后台线程中处理分析
        def process_analysis(app, analysis_id, user_id, image_data):
            with app.app_context():  # 确保在应用上下文中运行
                try:
                    # 重新获取分析记录
                    exam_analysis = ExamAnalysis.query.get(analysis_id)
                    if not exam_analysis:
                        print(f"错误：找不到分析记录ID={analysis_id}")
                        return
                        
                    print(f"开始处理分析，分析ID: {analysis_id}")
                    
                    # 1. 试卷分析 (使用 GLM-4V 直接分析图片)
                    print("开始分析试卷内容 (GLM-4V)")
                    analysis_result, error = analyze_exam_paper_with_vision(image_data)
                    if error:
                        print(f"试卷分析失败: {error}")
                        exam_analysis.status = 'failed'
                        exam_analysis.error_message = f'试卷分析失败: {error}'
                        db.session.commit()
                        return
                    print("试卷分析成功")
                    
                    # 2. 更新分析记录
                    print("更新分析记录")
                    
                    mistakes_data = analysis_result.get('mistakes', [])
                    cleaned_marks = build_exam_marks(mistakes_data)

                    exam_analysis.subject = analysis_result.get('subject', '未知科目')
                    exam_analysis.set_weak_points(analysis_result.get('weak_points', []))
                    exam_analysis.set_suggestions(analysis_result.get('suggestions', []))
                    
                    # 保存统一结构的批改摘要，前端展示直接复用这一份数据
                    exam_analysis.set_marks(cleaned_marks)
                    exam_analysis.status = 'extracting_mistakes'
                    db.session.commit()
                    print("分析记录更新成功，开始后台整理错题")
                    
                    # 接下来在后台静默处理错题和举一反三练习题
                    try:
                        print("开始整理错题本...")
                        if not mistakes_data:
                            print("试卷全对或没有错题，无需提取错题详情")
                        else:
                            if any(question_text_needs_refinement(item.get('question_text'), item.get('stem_summary')) for item in mistakes_data):
                                print("检测到部分错题题干过短，开始基于原卷二次提取详细题目")
                                refined_mistakes, refine_error = extract_mistakes_with_vision(
                                    image_data,
                                    exam_analysis.subject,
                                    [
                                        {
                                            'question_no': item.get('question_no'),
                                            'stem_summary': item.get('stem_summary'),
                                            'error_text': item.get('raw_error_text') or item.get('error_text')
                                        }
                                        for item in mistakes_data
                                    ]
                                )
                                if refined_mistakes and not refine_error:
                                    mistakes_data = merge_refined_mistakes(mistakes_data, refined_mistakes)
                                else:
                                    print(f"二次提取题干失败，继续使用首轮结果: {refine_error}")

                            print(f"一次性提取到 {len(mistakes_data)} 道错题详情，准备直接入库")
                            for mistake in mistakes_data:
                                question_no = normalize_math_text(mistake.get('question_no')) or '未知题号'
                                display_question = build_display_question(
                                    question_no,
                                    mistake.get('question_text') or mistake.get('display_question') or ''
                                )
                                error_text = normalize_math_text(mistake.get('error_text'))
                                explanation = normalize_math_text(mistake.get('explanation'))
                                explanation_parts = []
                                if error_text:
                                    explanation_parts.append(f"错误定位：{error_text}")
                                if explanation:
                                    explanation_parts.append(explanation)
                                full_explanation = "\n\n".join(explanation_parts) if explanation_parts else error_text

                                mistake_record = Mistake(
                                    user_id=user_id,
                                    exam_analysis_id=exam_analysis.id,
                                    exam_name_snapshot=exam_analysis.exam_name,
                                    exam_image_path_snapshot=exam_analysis.exam_image_path,
                                    subject=exam_analysis.subject,
                                    question_no=question_no,
                                    stem_summary=normalize_math_text(mistake.get('stem_summary')),
                                    question=display_question,
                                    user_answer=normalize_math_text(mistake.get('user_answer')),
                                    correct_answer=normalize_math_text(mistake.get('correct_answer')),
                                    explanation=full_explanation,
                                    error_type='未归类',
                                    is_mastered=False
                                )
                                db.session.add(mistake_record)
                            db.session.commit()
                            print("错题保存成功")

                            print("开始生成举一反三练习题...")
                            practice_questions, practice_error = generate_followup_practice_questions(
                                analysis_result.get('weak_points', []),
                                exam_analysis.subject,
                                mistakes_data
                            )
                            if practice_questions and not practice_error:
                                saved_count = save_followup_practice_questions(
                                    user_id,
                                    exam_analysis.subject,
                                    practice_questions
                                )
                                print(f"举一反三练习题保存完成，数量: {saved_count}")
                            else:
                                print(f"未生成举一反三练习题: {practice_error or '模型未返回题目'}")
                            
                        # 最终完成
                        exam_analysis.status = 'completed'
                        db.session.commit()
                    except Exception as e:
                        print(f"后台错题处理时发生错误: {str(e)}")
                        print(f"错误详情: {traceback.format_exc()}")
                        # 发生异常也要更新为完成，防止一直卡在中间状态
                        exam_analysis.status = 'completed'
                        db.session.commit()
                    
                except Exception as e:
                    print(f"处理分析时发生致命错误: {str(e)}")
                    print(f"错误详情: {traceback.format_exc()}")
                    try:
                        exam_analysis = ExamAnalysis.query.get(analysis_id)
                        if exam_analysis:
                            exam_analysis.status = 'failed'
                            exam_analysis.error_message = f'处理失败: {str(e)}'
                            db.session.commit()
                    except Exception as inner_e:
                        print(f"更新分析状态失败: {str(inner_e)}")
                
        # 获取应用实例
        app = current_app._get_current_object()
        
        # 启动后台处理线程
        thread = threading.Thread(
            target=process_analysis, 
            args=(app, exam_analysis.id, user.id, image_data)
        )
        thread.daemon = True
        thread.start()
        
        print("试卷上传成功，开始后台分析")
        return jsonify({
            'success': True,
            'message': '试卷上传成功，正在分析中',
            'data': {
                'analysis_id': exam_analysis.id,
                'status': 'pending'
            }
        }), 200
        
    except Exception as e:
        print(f"处理请求时发生错误: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'处理请求失败: {str(e)}'
        }), 500

@jwt_required()
def get_exam_analyses():
    """获取用户的所有试卷分析记录"""
    try:
        user_id = get_jwt_identity()
        print(f"获取用户 ID={user_id} 的试卷分析记录")

        user = User.query.get(user_id)
        if not user:
            print(f"错误：用户 ID={user_id} 不存在")
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        # 获取用户的所有试卷分析
        analyses = ExamAnalysis.query.filter_by(user_id=user.id).order_by(ExamAnalysis.created_at.desc()).all()
        print(f"找到 {len(analyses)} 条分析记录")
        
        return jsonify({
            'success': True,
            'data': [sanitize_exam_analysis_payload(analysis.to_dict()) for analysis in analyses]
        }), 200
        
    except Exception as e:
        error_message = str(e)
        print(f"获取分析记录失败: {error_message}")
        return jsonify({'success': False, 'message': f'获取分析记录失败: {error_message}'}), 500

def get_exam_analysis_detail(analysis_id):
    """获取试卷分析详情"""
    try:
        print(f"获取分析ID={analysis_id}的详情")
        
        analysis = ExamAnalysis.query.get(analysis_id)
        if not analysis:
            print(f"错误：分析记录ID={analysis_id}不存在")
            return jsonify({'success': False, 'message': '分析记录不存在'}), 404
        
        #print(f"成功获取分析记录详情，分析ID={analysis_id}")
        
        return jsonify({
            'success': True,
            'data': sanitize_exam_analysis_payload(analysis.to_dict())
        }), 200
        
    except Exception as e:
        error_message = str(e)
        print(f"获取分析详情失败: {error_message}")
        return jsonify({'success': False, 'message': f'获取分析详情失败: {error_message}'}), 500

def delete_exam_analysis(analysis_id):
    """删除指定的试卷分析记录"""
    try:
        print(f"收到删除分析记录请求，ID: {analysis_id}")
        analysis = ExamAnalysis.query.get(analysis_id)
        
        if not analysis:
            return jsonify({'success': False, 'message': '找不到该记录'}), 404
            
        # 可选：如果希望连带删除本地的图片文件
        if analysis.exam_image_path:
            # 去除前缀获取相对路径或绝对路径
            import os
            # 假设路径是以 /static 开头
            if analysis.exam_image_path.startswith('/static'):
                # 尝试构建本地物理路径并删除
                file_path = os.path.join(current_app.root_path, analysis.exam_image_path.lstrip('/'))
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"删除关联图片文件失败: {e}")
        
        db.session.delete(analysis)
        db.session.commit()
        
        print(f"成功删除分析记录 ID: {analysis_id}")
        return jsonify({'success': True, 'message': '记录删除成功'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"删除记录失败: {str(e)}")
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

def detect_subject(exam_name):
    """从试卷名称中检测科目"""
    exam_name = exam_name.lower()
    subjects = {
        '数学': ['数学', 'math'],
        '语文': ['语文', 'chinese'],
        '英语': ['英语', 'english'],
        '物理': ['物理', 'physics'],
        '化学': ['化学', 'chemistry'],
        '生物': ['生物', 'biology'],
        '政治': ['政治', 'politics'],
        '历史': ['历史', 'history'],
        '地理': ['地理', 'geography']
    }
    
    for subject, keywords in subjects.items():
        for keyword in keywords:
            if keyword in exam_name:
                return subject
    
    # 默认返回"未知科目"
    return "未知科目" 
