from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from models import User, Mistake, PracticeQuestion, ExamAnalysis
from extension import db
import logging
from collections import defaultdict
from functools import lru_cache
import json

logger = logging.getLogger(__name__)

report_bp = Blueprint('report', __name__)

# ==================== 辅助函数 ====================

def get_date_range(days=7):
    """生成日期范围列表"""
    today = datetime.now().date()
    return [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

def format_date(date_obj, format_str='%m-%d'):
    """格式化日期"""
    return date_obj.strftime(format_str)

def group_by_date(records, date_field='created_at'):
    """将记录按日期分组"""
    grouped = defaultdict(list)
    for record in records:
        date_key = getattr(record, date_field).strftime('%m-%d')
        grouped[date_key].append(record)
    return grouped

def count_by_date(records, date_field='created_at'):
    """统计每天记录数量"""
    counts = defaultdict(int)
    for record in records:
        date_key = getattr(record, date_field).strftime('%m-%d')
        counts[date_key] += 1
    return counts

def generate_parent_advice(recent_mistakes, recent_practices):
    """生成家长辅导话术（模拟AI生成）"""
    # 实际项目中这里应该调用真实的AI接口
    # 这里提供模拟数据
    advice = {
        'tutoring_advice': '根据本周错题数据，建议重点关注概念理解和计算准确性。',
        'summary': f'本周共产生 {len(recent_mistakes)} 个错题，表现平稳。',
        'suggestion': '建议每天安排15分钟专项练习，巩固薄弱知识点。'
    }
    
    # 如果有错题，根据错题类型提供更具体的建议
    if recent_mistakes:
        error_types = {}
        for m in recent_mistakes:
            e_type = getattr(m, 'error_type', '未归类')
            error_types[e_type] = error_types.get(e_type, 0) + 1
        
        if error_types:
            most_common = max(error_types.items(), key=lambda x: x[1])
            advice['suggestion'] = f'重点攻克"{most_common[0]}"类错误，占总错题的{most_common[1]}个。建议针对性练习。'
    
    return advice

def calculate_mastery_rate(daily_practices):
    """计算掌握率"""
    if not daily_practices:
        return 0
    mastered = sum(1 for p in daily_practices if getattr(p, 'is_mastered', False))
    return int((mastered / len(daily_practices)) * 100)

def get_weekly_stats(user_id, date_range):
    """获取每周统计数据（使用数据库聚合查询优化）"""
    start_date = date_range[0]
    end_date = date_range[-1] + timedelta(days=1)  # 包含结束日期
    
    # 使用数据库聚合查询
    from sqlalchemy import func
    
    # 按日期分组统计错题数
    mistake_stats = db.session.query(
        func.date(Mistake.created_at).label('date'),
        func.count(Mistake.id).label('count')
    ).filter(
        Mistake.user_id == user_id,
        Mistake.created_at >= start_date,
        Mistake.created_at < end_date
    ).group_by(func.date(Mistake.created_at)).all()
    
    # 按日期分组统计练习题数
    practice_stats = db.session.query(
        func.date(PracticeQuestion.created_at).label('date'),
        func.count(PracticeQuestion.id).label('total'),
        func.sum(PracticeQuestion.is_mastered.cast(db.Integer)).label('mastered')
    ).filter(
        PracticeQuestion.user_id == user_id,
        PracticeQuestion.created_at >= start_date,
        PracticeQuestion.created_at < end_date
    ).group_by(func.date(PracticeQuestion.created_at)).all()
    
    return mistake_stats, practice_stats

# ==================== 核心API ====================

@report_bp.route('/parent-dashboard/<username>', methods=['GET'])
def get_parent_dashboard(username):
    """获取家长辅导面板数据（周报、话术建议、雷达图、折线图等）- 优化版"""
    try:
        # 1. 获取用户
        user = User.query.filter_by(username=username).first()
        if not user:
            logger.warning(f"用户 {username} 不存在")
            return jsonify({
                'success': False,
                'message': f'用户 {username} 不存在'
            }), 404
        
        # 2. 定义时间范围
        days = 7
        today = datetime.now().date()
        start_date = today - timedelta(days=days)
        
        # 3. 使用数据库查询优化（一次性获取所有需要的数据）
        # 3.1 获取本周错题
        recent_mistakes = Mistake.query.filter(
            Mistake.user_id == user.id,
            Mistake.created_at >= start_date
        ).all()
        
        # 3.2 获取本周练习题
        recent_practices = PracticeQuestion.query.filter(
            PracticeQuestion.user_id == user.id,
            PracticeQuestion.created_at >= start_date
        ).all()
        
        # 4. 数据统计和分组（使用字典优化）
        # 4.1 错题归因分析（饼图数据）
        error_type_counts = defaultdict(int)
        for mistake in recent_mistakes:
            error_type = getattr(mistake, 'error_type', None) or '未归类'
            error_type_counts[error_type] += 1
        
        # 生成饼图数据
        pie_series_data = [
            {"name": k, "value": v} 
            for k, v in error_type_counts.items() 
            if v > 0
        ]
        
        # 如果没有数据，提供默认值
        if not pie_series_data:
            pie_series_data = [{"name": "暂无错题", "value": 1}]
        
        pie_data = {
            "series": [{"data": pie_series_data}]
        }
        
        # 4.2 掌握率趋势（折线图数据）- 使用字典优化
        # 生成日期列表
        dates = [format_date(today - timedelta(days=i)) for i in range(days - 1, -1, -1)]
        
        # 使用字典按日期分组练习题
        practice_by_date = group_by_date(recent_practices, 'created_at')
        
        # 按日期统计错题数量
        mistake_count_by_date = count_by_date(recent_mistakes, 'created_at')
        
        # 计算每天掌握率
        mastery_rate_data = []
        for date_key in dates:
            daily_practices = practice_by_date.get(date_key, [])
            daily_mistakes = mistake_count_by_date.get(date_key, 0)
            
            # 计算掌握率
            rate = calculate_mastery_rate(daily_practices)
            
            # 根据错题数调整掌握率（影响真实度）
            if rate > 0:
                rate = max(0, rate - daily_mistakes * 5)
            
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
        
        # 5. 生成AI辅导话术
        ai_advice = generate_parent_advice(recent_mistakes, recent_practices)
        
        # 6. 返回响应
        return jsonify({
            'success': True,
            'data': {
                'report_date_range': f"{start_date.strftime('%Y.%m.%d')} - {today.strftime('%m.%d')}",
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
        logger.error(f"获取家长面板数据失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@report_bp.route('/weekly-report/<username>', methods=['GET'])
def get_weekly_report(username):
    """获取更详细的周报数据 - 新增优化接口"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': f'用户 {username} 不存在'
            }), 404
        
        # 获取日期范围参数
        days = int(request.args.get('days', 7))
        if days > 30:  # 限制最大查询范围
            days = 30
        
        today = datetime.now().date()
        start_date = today - timedelta(days=days)
        
        # 使用数据库聚合查询优化
        mistake_stats, practice_stats = get_weekly_stats(user.id, 
            [start_date, today])
        
        # 构建完整的数据报告
        date_range = get_date_range(days)
        
        # 转换为字典便于快速查找
        mistake_dict = {record.date.strftime('%m-%d'): record.count 
                       for record in mistake_stats}
        practice_dict = {}
        for record in practice_stats:
            date_key = record.date.strftime('%m-%d')
            practice_dict[date_key] = {
                'total': record.total,
                'mastered': record.mastered or 0
            }
        
        # 生成每日数据
        daily_data = []
        for date_obj in date_range:
            date_key = date_obj.strftime('%m-%d')
            practice_info = practice_dict.get(date_key, {'total': 0, 'mastered': 0})
            
            daily_data.append({
                'date': date_key,
                'mistakes': mistake_dict.get(date_key, 0),
                'practices': practice_info['total'],
                'mastered': practice_info['mastered'],
                'mastery_rate': calculate_mastery_rate_value(
                    practice_info['total'],
                    practice_info['mastered']
                )
            })
        
        # 计算汇总统计
        total_mistakes = sum(d['mistakes'] for d in daily_data)
        total_practices = sum(d['practices'] for d in daily_data)
        total_mastered = sum(d['mastered'] for d in daily_data)
        
        return jsonify({
            'success': True,
            'data': {
                'date_range': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': today.strftime('%Y-%m-%d'),
                    'days': days
                },
                'daily_data': daily_data,
                'summary': {
                    'total_mistakes': total_mistakes,
                    'total_practices': total_practices,
                    'total_mastered': total_mastered,
                    'overall_mastery_rate': calculate_mastery_rate_value(
                        total_practices, total_mastered
                    ),
                    'avg_daily_mistakes': round(total_mistakes / days, 1) if days > 0 else 0
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取周报失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@report_bp.route('/error-analysis/<username>', methods=['GET'])
def get_error_analysis(username):
    """获取错题分析数据 - 新增接口"""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': f'用户 {username} 不存在'
            }), 404
        
        # 获取时间范围参数
        days = int(request.args.get('days', 30))
        if days > 90:  # 限制最大90天
            days = 90
        
        start_date = datetime.now() - timedelta(days=days)
        
        # 查询错题并分析
        mistakes = Mistake.query.filter(
            Mistake.user_id == user.id,
            Mistake.created_at >= start_date
        ).all()
        
        # 按错误类型统计
        error_type_stats = defaultdict(lambda: {'count': 0, 'subjects': set()})
        for mistake in mistakes:
            error_type = getattr(mistake, 'error_type', '未归类')
            subject = getattr(mistake, 'subject', '未知')
            error_type_stats[error_type]['count'] += 1
            error_type_stats[error_type]['subjects'].add(subject)
        
        # 按学科统计
        subject_stats = defaultdict(int)
        for mistake in mistakes:
            subject = getattr(mistake, 'subject', '未知')
            subject_stats[subject] += 1
        
        return jsonify({
            'success': True,
            'data': {
                'total_mistakes': len(mistakes),
                'time_range_days': days,
                'error_type_analysis': [
                    {
                        'type': k,
                        'count': v['count'],
                        'subjects': list(v['subjects'])
                    }
                    for k, v in error_type_stats.items()
                ],
                'subject_analysis': [
                    {'subject': k, 'count': v}
                    for k, v in subject_stats.items()
                ],
                'trend_data': generate_trend_data(mistakes, days)
            }
        })
        
    except Exception as e:
        logger.error(f"获取错题分析失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def calculate_mastery_rate_value(total, mastered):
    """计算掌握率百分比"""
    if total == 0:
        return 0
    return int((mastered / total) * 100)


def generate_trend_data(mistakes, days):
    """生成趋势数据"""
    from collections import Counter
    
    # 按日期统计错题
    date_counts = Counter()
    for mistake in mistakes:
        date_key = mistake.created_at.strftime('%m-%d')
        date_counts[date_key] += 1
    
    # 生成完整日期范围
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime('%m-%d') 
             for i in range(days - 1, -1, -1)]
    
    return [
        {'date': d, 'count': date_counts.get(d, 0)}
        for d in dates
    ]


# ==================== 缓存优化接口 ====================

@report_bp.route('/dashboard-cache/<username>', methods=['GET'])
def get_cached_dashboard(username):
    """获取缓存的面板数据 - 减少重复计算"""
    # 实际项目中使用Redis等缓存
    # 这里仅作示例
    try:
        # 检查缓存是否存在
        cache_key = f"dashboard:{username}:{datetime.now().strftime('%Y%m%d')}"
        
        # 模拟从缓存获取
        # cached_data = redis_client.get(cache_key)
        # if cached_data:
        #     return jsonify(json.loads(cached_data))
        
        # 缓存未命中，生成数据
        response = get_parent_dashboard(username)
        
        # 存储到缓存（模拟）
        # redis_client.setex(cache_key, 3600, response.get_data())
        
        return response
        
    except Exception as e:
        logger.error(f"获取缓存面板数据失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@report_bp.route('/batch-reports', methods=['POST'])
def get_batch_reports():
    """批量获取多个用户报告 - 优化批量查询"""
    try:
        data = request.json
        usernames = data.get('usernames', [])
        
        if not usernames or len(usernames) > 50:  # 限制批量大小
            return jsonify({
                'success': False,
                'message': '请提供有效的用户名列表，最多50个'
            }), 400
        
        # 批量查询用户
        users = User.query.filter(User.username.in_(usernames)).all()
        user_map = {user.username: user for user in users}
        
        # 批量查询统计数据
        user_ids = [user.id for user in users]
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        # 批量获取错题统计
        mistake_counts = db.session.query(
            Mistake.user_id,
            func.count(Mistake.id).label('count')
        ).filter(
            Mistake.user_id.in_(user_ids),
            Mistake.created_at >= seven_days_ago
        ).group_by(Mistake.user_id).all()
        
        mistake_count_map = {mc.user_id: mc.count for mc in mistake_counts}
        
        # 构建响应
        reports = []
        for username in usernames:
            user = user_map.get(username)
            if user:
                reports.append({
                    'username': username,
                    'success': True,
                    'data': {
                        'weekly_mistakes': mistake_count_map.get(user.id, 0),
                        'has_data': user.id in mistake_count_map
                    }
                })
            else:
                reports.append({
                    'username': username,
                    'success': False,
                    'message': '用户不存在'
                })
        
        return jsonify({
            'success': True,
            'data': reports
        })
        
    except Exception as e:
        logger.error(f"批量获取报告失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500