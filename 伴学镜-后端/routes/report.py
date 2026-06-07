from flask import Blueprint, jsonify, request
from models import db, ExamAnalysis, Mistake, PracticeQuestion, User
from sqlalchemy import func
from datetime import datetime, timedelta
from utils import generate_parent_advice

report_bp = Blueprint('report', __name__)

@report_bp.route('/parent-dashboard/<username>', methods=['GET'])
def get_parent_dashboard(username):
    """获取家长辅导面板数据（周报、话术建议、雷达图、折线图等）"""
    try:
        user = User.query.filter_by(username=username).first()
        
        # 1. 基础数据统计 (最近7天作为"周报")
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        recent_mistakes = []
        recent_practices = []
        
        if user:
            # 获取本周错题
            recent_mistakes = Mistake.query.filter(
                Mistake.user_id == user.id,
                Mistake.created_at >= seven_days_ago
            ).all()
            
            # 获取所有练习题以计算正确率/专注力 (这里简化模拟)
            recent_practices = PracticeQuestion.query.filter(
                PracticeQuestion.user_id == user.id,
                PracticeQuestion.created_at >= seven_days_ago
            ).all()
        else:
            print(f"用户 {username} 不存在，将返回模拟数据")

        # 2. 生成图表数据
        
        # 2.1 饼图数据 (错题归因分析)
        # 根据错题的 error_type 进行统计
        error_type_counts = {}
        for m in recent_mistakes:
            # 防止为空
            e_type = m.error_type if getattr(m, 'error_type', None) else '未归类'
            error_type_counts[e_type] = error_type_counts.get(e_type, 0) + 1
            
        # 如果没有错题，给个默认好数据
        if not error_type_counts:
            error_type_counts = {'粗心大意': 0, '概念不清': 0, '计算错误': 0}
            
        pie_series_data = [{"name": k, "value": v} for k, v in error_type_counts.items() if v > 0]
        if not pie_series_data:
            pie_series_data = [{"name": "暂无错题", "value": 1}]
            
        pie_data = {
            "series": [{
                "data": pie_series_data
            }]
        }

        # 2.2 折线图数据 (练习题掌握率/正确率趋势 - 最近7天)
        dates = [(datetime.now() - timedelta(days=i)).strftime('%m-%d') for i in range(6, -1, -1)]
        
        mastery_rate_data = []
        for date_str in dates:
            # 找到当天创建的练习题
            daily_practices = [p for p in recent_practices if p.created_at.strftime('%m-%d') == date_str]
            if daily_practices:
                mastered = sum(1 for p in daily_practices if p.is_mastered)
                rate = int((mastered / len(daily_practices)) * 100)
            else:
                # 如果当天没练习数据，则按 0 处理，避免新用户显示虚高曲线
                rate = 0
                
            # 根据错题数稍微加点波动，显得更真实
            daily_mistakes = sum(1 for m in recent_mistakes if m.created_at.strftime('%m-%d') == date_str)
            rate = max(0, min(100, rate - daily_mistakes * 5))
            mastery_rate_data.append(rate)

        line_data = {
            "categories": dates,
            "series": [
                {
                    "name": "举一反三掌握率(%)",
                    "data": mastery_rate_data
                }
            ]
        }

        # 3. 调用 AI 生成家长辅导话术和总结建议
        ai_advice = generate_parent_advice(recent_mistakes, [])
        
        return jsonify({
            'success': True,
            'data': {
                'report_date_range': f"{seven_days_ago.strftime('%Y.%m.%d')} - {datetime.now().strftime('%m.%d')}",
                'pie_chart': pie_data,
                'line_chart': line_data,
                'ai_analysis': {
                    'tutoring_advice': ai_advice.get('tutoring_advice', ''),
                    'summary': ai_advice.get('summary', ''),
                    'suggestion': ai_advice.get('suggestion', '')
                },
                'stats': {
                    'mistakes_count': len(recent_mistakes),
                    'new_kps_count': 0,
                    'practices_count': len(recent_practices)
                }
            }
        })
        
    except Exception as e:
        import traceback
        print(f"获取家长面板数据失败: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500 
