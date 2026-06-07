from datetime import datetime
from extension import db
import json

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(500), default='https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png')
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_avatar_url(self):
        avatar_url = self.avatar
        if avatar_url and avatar_url.startswith('/static'):
            avatar_url = f"http://192.168.31.138:5000{avatar_url}"
        return avatar_url

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar': self.get_avatar_url(),
            'created_at': self.created_at.isoformat()
        }

    def to_profile_dict(self, stats=None):
        stats = stats or {}
        learning_days = stats.get('learning_days')
        if learning_days is None:
            learning_days = max((datetime.utcnow().date() - self.created_at.date()).days + 1, 1)

        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar': self.get_avatar_url(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_at_label': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
            'learning_days': learning_days,
            'stats': {
                'exam_count': stats.get('exam_count', 0),
                'mistake_count': stats.get('mistake_count', 0),
                'mastered_count': stats.get('mastered_count', 0),
                'practice_count': stats.get('practice_count', 0),
                'subject_count': stats.get('subject_count', 0)
            }
        }

class ExamAnalysis(db.Model):
    """试卷分析记录"""
    __tablename__ = 'exam_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_name = db.Column(db.String(200), nullable=False)
    exam_image_path = db.Column(db.String(500))
    extracted_text = db.Column(db.Text)
    subject = db.Column(db.String(50))  # 添加科目字段
    weak_points = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    marks = db.Column(db.Text)  # 新增: 存储试卷批改坐标的JSON
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系定义
    user = db.relationship('User', backref=db.backref('exam_analyses', lazy=True))

    def set_weak_points(self, points_list):
        self.weak_points = json.dumps(points_list, ensure_ascii=False)
    
    def get_weak_points(self):
        if self.weak_points:
            return json.loads(self.weak_points)
        return []
    
    def set_suggestions(self, suggestions_list):
        self.suggestions = json.dumps(suggestions_list, ensure_ascii=False)
    
    def get_suggestions(self):
        if self.suggestions:
            return json.loads(self.suggestions)
        return []
        
    def set_marks(self, marks_list):
        self.marks = json.dumps(marks_list, ensure_ascii=False)
        
    def get_marks(self):
        if self.marks:
            return json.loads(self.marks)
        return []
    
    def to_dict(self):
        return {
            'id': self.id,
            'exam_name': self.exam_name,
            'exam_image_path': self.exam_image_path,
            'extracted_text': self.extracted_text,
            'weak_points': self.get_weak_points(),
            'suggestions': self.get_suggestions(),
            'marks': self.get_marks(), # 暴露给前端
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'subject': self.subject  # 新增科目字段
        }

class Mistake(db.Model):
    """错题记录"""
    __tablename__ = 'mistakes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_analysis_id = db.Column(db.Integer, db.ForeignKey('exam_analyses.id'))
    exam_name_snapshot = db.Column(db.String(200))
    exam_image_path_snapshot = db.Column(db.String(500))
    subject = db.Column(db.String(50), nullable=False)
    question_no = db.Column(db.String(100))
    stem_summary = db.Column(db.String(255))
    question = db.Column(db.Text, nullable=False)
    user_answer = db.Column(db.Text)
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)
    error_type = db.Column(db.String(50), default='未归类') # 新增：错题原因分类（如粗心大意、概念不清等）
    is_mastered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系定义
    user = db.relationship('User', backref=db.backref('mistakes', lazy=True))
    exam_analysis = db.relationship('ExamAnalysis', backref=db.backref('mistakes', lazy=True))
    
    def to_dict(self):
        exam_name = self.exam_name_snapshot
        exam_image_path = self.exam_image_path_snapshot

        if self.exam_analysis:
            exam_name = exam_name or self.exam_analysis.exam_name
            exam_image_path = exam_image_path or self.exam_analysis.exam_image_path

        return {
            'id': self.id,
            'subject': self.subject,
            'exam_analysis_id': self.exam_analysis_id,
            'exam_name': exam_name,
            'exam_image_path': exam_image_path,
            'question_no': self.question_no,
            'stem_summary': self.stem_summary,
            'question': self.question,
            'user_answer': self.user_answer,
            'correct_answer': self.correct_answer,
            'explanation': self.explanation,
            'error_type': self.error_type,
            'is_mastered': self.is_mastered,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class PracticeQuestion(db.Model):
    """练习题模型"""
    __tablename__ = 'practice_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    question = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # choice/fill/large
    options = db.Column(db.JSON)  # 仅选择题需要
    answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(10))  # easy/medium/hard
    steps = db.Column(db.JSON)  # 仅大题需要，存储解题步骤
    is_mastered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联用户
    user = db.relationship('User', backref=db.backref('practice_questions', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'question': self.question,
            'question_type': self.question_type,
            'options': self.options,
            'answer': self.answer,
            'explanation': self.explanation,
            'difficulty': self.difficulty,
            'steps': self.steps,  # 添加步骤字段
            'is_mastered': self.is_mastered,
            'created_at': self.created_at.isoformat()
        }
