import os
import re
from zhipuai import ZhipuAI
import time
import traceback
import base64
import json
from extension import db
from models import PracticeQuestion

# 初始化 智谱AI 客户端
zhipu_client = ZhipuAI(api_key="d2484d6c235a45d68c7d67d4568170db.YR7b6W0V9yUPzqui")

UNSUPPORTED_EXAM_UPLOAD_MESSAGE = '当前图片不是可批改的试卷、作业或练习题，请上传包含题目内容的清晰学习资料图片后再试。'


def _prepare_image_url(base64_data):
    """统一处理视觉模型所需的图片 URL。"""
    if not base64_data.startswith('data:image'):
        return f"data:image/jpeg;base64,{base64_data}"
    return base64_data


def _extract_json_payload(content):
    if not content:
        return ""

    text = content.strip()
    fenced_match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()

    generic_fenced_match = re.search(r'```\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if generic_fenced_match:
        return generic_fenced_match.group(1).strip()

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()

    return text


def _repair_json_backslashes(json_str):
    if not json_str:
        return json_str

    repaired = json_str
    repaired = repaired.replace('\\n', '___NEWLINE___')
    repaired = repaired.replace('\\"', '___QUOTE___')
    repaired = repaired.replace('\\t', '___TAB___')
    repaired = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', repaired)
    repaired = repaired.replace('___NEWLINE___', '\\n')
    repaired = repaired.replace('___QUOTE___', '\\"')
    repaired = repaired.replace('___TAB___', '\\t')
    return repaired


def _escape_invalid_backslashes_in_strings(json_str):
    """只在 JSON 字符串内部修复非法反斜杠，避免触发 Invalid \\escape。"""
    if not json_str:
        return json_str

    result = []
    in_string = False
    escaped = False
    valid_escapes = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}
    length = len(json_str)

    for index, char in enumerate(json_str):
        if not in_string:
            result.append(char)
            if char == '"':
                in_string = True
                escaped = False
            continue

        if escaped:
            if char not in valid_escapes:
                result.append('\\')
            result.append(char)
            escaped = False
            continue

        if char == '\\':
            next_char = json_str[index + 1] if index + 1 < length else ''
            if next_char in valid_escapes:
                result.append(char)
                escaped = True
            else:
                result.append('\\\\')
            continue

        result.append(char)
        if char == '"':
            in_string = False

    return ''.join(result)


def _repair_common_json_issues(json_str):
    if not json_str:
        return json_str

    repaired = json_str.strip()
    repaired = repaired.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    repaired = repaired.replace('\ufeff', '')

    # Remove trailing commas before object/array endings.
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

    # Insert missing commas between adjacent JSON values/keys on separate lines.
    repaired = re.sub(r'([}\]"])\s*\n\s*(")', r'\1,\n\2', repaired)
    repaired = re.sub(r'([0-9}\]"])\s*\n\s*(")', r'\1,\n\2', repaired)
    repaired = re.sub(r'([}\]"])\s*\n\s*(\{)', r'\1,\n\2', repaired)

    # If the model appends explanation text after the last object, keep only the outer JSON block.
    start = repaired.find('{')
    end = repaired.rfind('}')
    if start != -1 and end != -1 and end > start:
        repaired = repaired[start:end + 1]

    return repaired


def repair_json_with_model(bad_content):
    """Use a lightweight model call to repair malformed JSON without changing meaning."""
    prompt = f"""You are a JSON repair tool.
Fix the following content into valid JSON only.
Rules:
1. Preserve the original meaning and fields.
2. Do not add explanations or markdown.
3. Only fix JSON syntax, escaping, commas, quotes, and brackets.
4. Return one valid JSON object only.

Bad content:
{bad_content}
"""

    response = zhipu_client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return _extract_json_payload(response.choices[0].message.content)


def _normalize_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    return text in {'true', '1', 'yes', 'y', '是', '支持', '可批改'}


def _normalize_supported_learning_result(raw_result):
    if not isinstance(raw_result, dict):
        raw_result = {}

    material_type = normalize_math_text(
        raw_result.get('material_type') or raw_result.get('category') or 'unknown'
    )
    confidence = normalize_math_text(raw_result.get('confidence') or 'low').lower()
    if confidence not in {'high', 'medium', 'low'}:
        confidence = 'low'

    reason = normalize_math_text(raw_result.get('reason') or raw_result.get('message'))

    return {
        'is_learning_material': _normalize_bool(
            raw_result.get('is_learning_material') or raw_result.get('is_supported')
        ),
        'material_type': material_type or 'unknown',
        'confidence': confidence,
        'reason': reason
    }


def detect_supported_learning_material_with_vision(base64_data, exam_name=""):
    """识别图片是否为可进入拍照批改流程的学习题目材料。"""
    try:
        image_url = _prepare_image_url(base64_data)
        exam_name_hint = normalize_math_text(exam_name)
        prompt = f"""你是“拍照批改”上传前置审核助手，需要判断这张图片是否适合进入试卷/作业批改流程。

上传名称参考：{exam_name_hint or '未提供'}

判定为 true 的情况：
1. 试卷、测试卷、练习卷、作业页、练习册页面。
2. 课本或教辅上的题目页，能看出明确题目、选项、填空、解答题、作答痕迹等。
3. 其它明显属于学生做题场景、且内容以“题目”为主的学习材料。

判定为 false 的情况：
1. 人物、风景、商品、票据、聊天截图、海报、证件、表格、通知、课表等非学习题目图片。
2. 纯笔记、纯知识点整理、纯文字材料、作文正文、教材目录、封面、空白纸张。
3. 图片过于模糊，无法确认存在可批改题目。
4. 虽然与学习有关，但没有具体题目可供批改。

只返回一个 JSON 对象，不要 markdown，不要解释：
{{
  "is_learning_material": true,
  "material_type": "exam/homework/workbook/textbook_questions/notes/non_learning/unclear/other",
  "confidence": "high/medium/low",
  "reason": "一句简短原因"
}}"""

        response = zhipu_client.chat.completions.create(
            model="glm-4v-plus",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        )

        parsed = parse_model_json(response.choices[0].message.content)
        return _normalize_supported_learning_result(parsed), None
    except Exception as e:
        error_msg = f"上传内容识别失败: {str(e)}"
        print(error_msg)
        print(f"错误详情: {traceback.format_exc()}")
        return None, error_msg


def request_exam_analysis(image_url, outline, strict_mode=False):
    if strict_mode:
        prompt = f"""Return one valid JSON object only.
No markdown. No comments. No extra text.

Known question outline:
{json.dumps(outline, ensure_ascii=False)}

Required JSON schema:
{{
  "subject": "subject name",
  "weak_points": ["weak point 1", "weak point 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "mistakes": [
    {{
      "outline_id": 1,
      "question_no": "precise question number",
      "question_type": "choice/fill/short/large/other",
      "stem_summary": "short stem summary",
      "error_text": "concise mistake description",
      "question_text": "full original question text",
      "user_answer": "student wrong answer or wrong step",
      "correct_answer": "correct answer or correct step",
      "explanation": "clear explanation",
      "knowledge_points": ["kp1", "kp2"]
    }}
  ]
}}

Rules:
1. The response must be valid JSON parseable by Python json.loads.
2. Do not omit commas.
3. Escape quotes inside strings correctly.
4. Use plain readable math text only.
5. Reuse the provided question_no whenever possible.
6. Prefer hierarchical locations such as "第3大题(2)" or "第2大题第1小题".
7. Do not use vague labels like "第1题", "第2题" unless the paper truly has no major-section structure."""
    else:
        prompt = f"""You are a strict exam-review assistant.
Return JSON only. Do not include markdown or extra explanation.

Known question outline from the same paper:
{json.dumps(outline, ensure_ascii=False)}

Tasks:
1. Find every wrong answer on the paper.
2. Reuse the provided question_no whenever possible, including major/minor sub-question structure.
3. Output one unified structured result for frontend display, mistake-book storage, and follow-up practice generation.

Rules:
1. Output each wrong question once only.
2. Each mistake must copy one outline_id from the known question outline above.
3. question_no must copy the matched outline item's question_no exactly. Do not invent or renumber it.
4. question_no must be precise and hierarchical. Prefer forms like "第3大题(2)" or "第2大题第1小题".
5. Do not output vague labels like "第1题" or "第2题" unless the original paper truly has no major-section structure.
6. stem_summary must be a short 8-20 character summary of the stem.
7. error_text must clearly say what went wrong in one short sentence.
8. For long-form questions, user_answer must point to the first wrong step, not only the final result.
9. correct_answer must match that step or sub-question.
10. question_text should stay faithful to the original paper. If unreadable, keep it empty instead of inventing content.
11. Use plain readable math text only. Do not output LaTeX wrappers such as $, $$, \\(...\\), or \\[...\\].
12. knowledge_points should contain only the most relevant 1-3 items.

Return this JSON schema:
{{
  "subject": "subject name",
  "weak_points": ["weak point 1", "weak point 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "mistakes": [
    {{
      "outline_id": 1,
      "question_no": "precise question number",
      "question_type": "choice/fill/short/large/other",
      "stem_summary": "short stem summary",
      "error_text": "concise mistake description",
      "question_text": "original question text",
      "user_answer": "student wrong answer or wrong step",
      "correct_answer": "correct answer or correct step",
      "explanation": "clear explanation",
      "knowledge_points": ["kp1", "kp2"]
    }}
  ]
}}"""

    response = zhipu_client.chat.completions.create(
        model="glm-4v-plus",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
    )
    return response.choices[0].message.content


def parse_model_json(content):
    """从大模型响应中尽可能稳健地提取 JSON。"""
    json_str = _extract_json_payload(content)
    if not json_str:
        raise json.JSONDecodeError("empty json", "", 0)

    candidates = [
        json_str,
        _escape_invalid_backslashes_in_strings(json_str),
        _repair_json_backslashes(json_str),
        _repair_common_json_issues(json_str),
        _escape_invalid_backslashes_in_strings(_repair_common_json_issues(json_str)),
        _repair_common_json_issues(_escape_invalid_backslashes_in_strings(json_str)),
        _repair_json_backslashes(_repair_common_json_issues(json_str)),
        _repair_json_backslashes(_escape_invalid_backslashes_in_strings(json_str)),
        json_str.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    ]

    last_error = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc

    try:
        repaired_by_model = repair_json_with_model(json_str)
        repaired_candidate = _repair_json_backslashes(
            _escape_invalid_backslashes_in_strings(
                _repair_common_json_issues(repaired_by_model)
            )
        )
        return json.loads(repaired_candidate)
    except Exception:
        pass

    raise last_error


def _replace_latex_fraction(text):
    pattern = re.compile(r'\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}')
    previous = None
    updated = text
    while previous != updated:
        previous = updated
        updated = pattern.sub(r'(\1)/(\2)', updated)
    return updated


def _replace_inline_powers(text):
    def replacer(match):
        base = match.group(1)
        exp = match.group(2)
        return f"{base}^{exp}"

    updated = re.sub(r'([A-Za-z0-9)\]])\^([0-9+\-=\(\)ni]{1,6})', replacer, text)
    updated = re.sub(r'([A-Za-z0-9)\]])\^\(([^\)]+)\)', r'\1^(\2)', updated)
    return updated


def _extract_short_thinking_hint(explanation):
    text = normalize_math_text(explanation)
    if not text:
        return ""

    for separator in ['。', '\n', '；', ';']:
        if separator in text:
            text = text.split(separator, 1)[0]
            break

    text = re.sub(r'^(解析|思路|关键是|方法是|注意|错误定位)[:：]\s*', '', text)
    text = text.strip('：:，,。 ')
    text = re.sub(r'[<>^`~]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > 60:
        text = text[:60].rstrip() + '...'
    return text


def normalize_math_text(value):
    """将大模型输出的数学文本尽量转成前端可直接展示的纯文本。"""
    if value is None:
        return ""

    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    elif not isinstance(value, str):
        value = str(value)

    text = value.strip()
    if not text:
        return ""

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('```', '')
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.S)
    text = re.sub(r'\$(.*?)\$', r'\1', text, flags=re.S)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text, flags=re.S)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text, flags=re.S)
    text = text.replace('\\left', '').replace('\\right', '')
    text = _replace_latex_fraction(text)
    text = re.sub(r'\\sqrt\s*\{([^{}]+)\}', r'sqrt(\1)', text)
    text = re.sub(r'\\text\s*\{([^{}]+)\}', r'\1', text)
    text = re.sub(r'\^\{([^{}]+)\}', r'^\1', text)
    text = re.sub(r'_\{([^{}]+)\}', r'_\1', text)

    replacements = {
        '\\times': '×',
        '\\cdot': '·',
        '\\div': '÷',
        '\\pm': '±',
        '\\mp': '∓',
        '\\neq': '!=',
        '\\leq': '<=',
        '\\geq': '>=',
        '\\approx': '约等于',
        '\\to': '->',
        '\\rightarrow': '->',
        '\\Rightarrow': '=>',
        '\\leftarrow': '<-',
        '\\mapsto': '->',
        '\\because': '因为',
        '\\therefore': '所以',
        '\\sin': 'sin',
        '\\cos': 'cos',
        '\\tan': 'tan',
        '\\cot': 'cot',
        '\\ln': 'ln',
        '\\log': 'log',
        '\\int': '积分',
        '\\sum': '求和',
        '\\triangle': '三角形',
        '\\angle': '角',
        '\\circ': '°',
        '\\pi': 'π'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace('→', '到').replace('⇒', '推出').replace('←', '从')
    text = _replace_inline_powers(text)
    text = re.sub(r'([A-Za-z0-9])_([0-9]+)', r'\1\2', text)
    text = text.replace('{', '').replace('}', '')
    text = text.replace('\\', '')
    text = text.replace('⁰', '^0').replace('¹', '^1').replace('²', '^2').replace('³', '^3')
    text = text.replace('⁴', '^4').replace('⁵', '^5').replace('⁶', '^6').replace('⁷', '^7')
    text = text.replace('⁸', '^8').replace('⁹', '^9').replace('ⁿ', '^n').replace('ⁱ', '^i')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _normalize_string_list(values):
    if not isinstance(values, list):
        return []

    result = []
    seen = set()
    for value in values:
        normalized = normalize_math_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_question_no(value, fallback_index):
    text = normalize_math_text(value)
    text = re.sub(r'^(题号|题目|位置)[:：]\s*', '', text)
    text = text.replace(' ', '')
    return text or f"第{fallback_index}处错误"


def _normalize_match_text(value):
    text = normalize_math_text(value).lower()
    text = re.sub(r'[【】\[\]（）()<>《》"“”‘’\s]', '', text)
    text = re.sub(r'[：:，,。；;、\-_=+*/\\|]', '', text)
    return text


def _is_vague_question_no(question_no):
    text = _normalize_question_no(question_no, 1)
    return bool(re.fullmatch(r'第[一二三四五六七八九十0-9]+题', text))


def _choose_outline_question_no(item, outline_questions, fallback_index):
    raw_question_no = _normalize_question_no(
        item.get('question_no') or item.get('original_question_no') or item.get('question_position'),
        fallback_index
    )
    outline_id = item.get('outline_id')
    stem_summary = normalize_math_text(item.get('stem_summary'))
    question_text = normalize_math_text(item.get('question_text') or item.get('question'))

    if not outline_questions:
        return raw_question_no, raw_question_no, outline_id

    normalized_outline_id = None
    generic_order = None
    try:
        if outline_id is not None and str(outline_id).strip():
            normalized_outline_id = int(str(outline_id).strip())
    except ValueError:
        normalized_outline_id = None
    generic_match = re.fullmatch(r'第([一二三四五六七八九十0-9]+)题', raw_question_no)
    if generic_match:
        generic_order = generic_match.group(1)

    if normalized_outline_id is not None:
        for outline in outline_questions:
            if outline.get('outline_id') == normalized_outline_id and outline.get('question_no'):
                return outline['question_no'], raw_question_no, normalized_outline_id

    normalized_raw = _normalize_match_text(raw_question_no)
    for outline in outline_questions:
        if _normalize_match_text(outline.get('question_no')) == normalized_raw and outline.get('question_no'):
            return outline['question_no'], raw_question_no, outline.get('outline_id')

    if not _is_vague_question_no(raw_question_no):
        return raw_question_no, raw_question_no, normalized_outline_id

    summary_key = _normalize_match_text(stem_summary)
    question_key = _normalize_match_text(question_text)
    summary_candidates = []
    for outline in outline_questions:
        outline_summary = _normalize_match_text(outline.get('stem_summary'))
        if summary_key and outline_summary and (summary_key in outline_summary or outline_summary in summary_key):
            summary_candidates.append(outline)
            continue
        if question_key and outline_summary and outline_summary in question_key:
            summary_candidates.append(outline)

    if len(summary_candidates) == 1:
        outline = summary_candidates[0]
        return outline['question_no'], raw_question_no, outline.get('outline_id')

    if len(summary_candidates) > 1 and generic_order:
        try:
            order_value = int(generic_order)
            if 1 <= order_value <= len(summary_candidates):
                outline = summary_candidates[order_value - 1]
                return outline['question_no'], raw_question_no, outline.get('outline_id')
        except ValueError:
            pass

    if summary_candidates:
        outline = summary_candidates[0]
        return outline['question_no'], raw_question_no, outline.get('outline_id')

    return raw_question_no, raw_question_no, normalized_outline_id


def simplify_question_no(value, fallback_index=None):
    text = _normalize_question_no(value, fallback_index or 1)
    text = text.replace('选择题', '').replace('填空题', '').replace('解答题', '').replace('判断题', '')
    text = re.sub(r'^第(\d+)大题第(\d+)小题$', r'第\1大题(\2)', text)
    text = re.sub(r'^第(\d+)大题第(\d+)问$', r'第\1大题(\2)', text)
    text = re.sub(r'^第([一二三四五六七八九十]+)大题第([一二三四五六七八九十]+)小题$', r'第\1大题(\2)', text)
    text = re.sub(r'^第([一二三四五六七八九十]+)大题第([一二三四五六七八九十]+)问$', r'第\1大题(\2)', text)
    text = re.sub(r'^第(\d+)小题$', r'第\1题', text)
    text = re.sub(r'^第(\d+)处错误$', r'第\1题', text)
    text = re.sub(r'^(第\d+大题)\((\d+)\)题$', r'\1(\2)', text)
    text = re.sub(r'^(第\d+题)目$', r'\1', text)
    return text[:16]


def _build_stem_summary(question_text):
    text = normalize_math_text(question_text)
    text = re.sub(r'^[（(]?\d+[)）.、]\s*', '', text)
    text = re.sub(r'^[一二三四五六七八九十]+[、.]\s*', '', text)
    if len(text) <= 28:
        return text
    return f"{text[:28].rstrip()}..."


def answers_mean_equivalent(user_answer, correct_answer):
    left = normalize_math_text(user_answer)
    right = normalize_math_text(correct_answer)
    if not left or not right:
        return False

    normalized_left = re.sub(r'\s+', '', left).lower()
    normalized_right = re.sub(r'\s+', '', right).lower()
    return normalized_left == normalized_right


def make_student_friendly_error_text(question_type, stem_summary, error_text, user_answer, correct_answer, explanation=""):
    summary = normalize_math_text(stem_summary)
    detail = normalize_math_text(error_text)
    user_text = normalize_math_text(user_answer)
    correct_text = normalize_math_text(correct_answer)
    hint = _extract_short_thinking_hint(explanation)
    q_type = (normalize_math_text(question_type) or 'unknown').lower()
    if '选择' in q_type:
        q_type = 'choice'
    elif '填空' in q_type:
        q_type = 'fill'
    elif '大题' in q_type or '解答' in q_type or '综合' in q_type:
        q_type = 'large'

    if user_text and correct_text and not answers_mean_equivalent(user_text, correct_text):
        if q_type == 'choice':
            return f"正确答案：{correct_text}；思路：{hint}" if hint else f"正确答案：{correct_text}"
        if q_type == 'fill':
            return f"正确答案：{correct_text}；思路：{hint}" if hint else f"正确答案：{correct_text}"
        if q_type == 'large':
            return f"错在关键步骤；正确应为：{correct_text}"
        if summary:
            return f"正确答案：{correct_text}；思路：{hint}" if hint else f"正确答案：{correct_text}"
        return f"正确答案：{correct_text}"

    if correct_text and q_type in {'choice', 'fill'}:
        return f"正确答案：{correct_text}；思路：{hint}" if hint else f"正确答案：{correct_text}"

    if detail:
        detail = re.sub(r'^(该题|这题|此题)', '', detail).strip('：:，,。 ')
        if summary:
            return f"{summary}：{detail}"
        return detail

    if summary:
        return f"{summary}：请回看关键步骤"
    return "请回看关键步骤"


def build_display_question(question_no, question_text):
    clean_question = normalize_math_text(question_text)
    if not clean_question:
        return f"【{question_no}】题目文字识别不清，请结合原试卷查看。"
    if clean_question.startswith(f"【{question_no}】"):
        return clean_question
    return f"【{question_no}】{clean_question}"


def question_text_needs_refinement(question_text, stem_summary=""):
    text = normalize_math_text(question_text)
    summary = normalize_math_text(stem_summary)
    text = re.sub(r'^【[^】]+】', '', text).strip()

    if not text:
        return True
    if summary and text == summary:
        return True
    if summary and len(text) <= len(summary) + 6:
        return True
    if len(text) <= 12:
        return True

    generic_patterns = [
        r'^求下列',
        r'^解下列',
        r'^计算下列',
        r'^已知.+求',
        r'^阅读材料',
        r'^根据.+回答',
        r'^回答下列问题',
        r'^下列.+的是',
        r'^判断下列'
    ]
    if any(re.search(pattern, text) for pattern in generic_patterns) and len(text) <= 24:
        return True

    return False


def should_use_refined_question_text(current_text, refined_text, stem_summary=""):
    current = normalize_math_text(current_text)
    refined = normalize_math_text(refined_text)
    summary = normalize_math_text(stem_summary)

    if not refined:
        return False
    if question_text_needs_refinement(current, summary) and not question_text_needs_refinement(refined, summary):
        return True
    if len(refined) >= len(current) + 8:
        return True
    return False


def merge_refined_mistakes(primary_mistakes, refined_mistakes):
    refined_map = {}
    for item in refined_mistakes or []:
        question_no = normalize_math_text(item.get('question_no'))
        if question_no:
            refined_map[question_no] = item

    merged = []
    for primary in primary_mistakes or []:
        updated = dict(primary)
        question_no = normalize_math_text(primary.get('question_no'))
        refined = refined_map.get(question_no)
        if refined:
            if should_use_refined_question_text(
                primary.get('question_text'),
                refined.get('question_text') or refined.get('question'),
                primary.get('stem_summary')
            ):
                updated['question_text'] = normalize_math_text(
                    refined.get('question_text') or refined.get('question')
                )
                updated['display_question'] = build_display_question(
                    question_no or '未知题号',
                    updated['question_text']
                )

            for field in ['user_answer', 'correct_answer', 'explanation']:
                primary_value = normalize_math_text(updated.get(field))
                refined_value = normalize_math_text(refined.get(field))
                if refined_value and len(refined_value) > len(primary_value):
                    updated[field] = refined_value

            primary_kps = updated.get('knowledge_points') or []
            refined_kps = refined.get('knowledge_points') or []
            if refined_kps and len(refined_kps) >= len(primary_kps):
                updated['knowledge_points'] = refined_kps

        merged.append(updated)
    return merged


def generate_followup_practice_questions(weak_points, subject, source_mistakes=None):
    """基于错题生成举一反三练习题，仅返回练习题数据，不再生成知识点或资源。"""
    try:
        weak_points = _normalize_string_list(weak_points)
        source_mistakes = source_mistakes or []
        grounded_mistakes = []

        for mistake in source_mistakes[:6]:
            if not isinstance(mistake, dict):
                continue
            grounded_mistakes.append({
                'question_no': normalize_math_text(mistake.get('question_no')),
                'stem_summary': normalize_math_text(mistake.get('stem_summary')),
                'question_text': normalize_math_text(mistake.get('question_text') or mistake.get('display_question')),
                'error_text': normalize_math_text(mistake.get('raw_error_text') or mistake.get('error_text')),
                'user_answer': normalize_math_text(mistake.get('user_answer')),
                'correct_answer': normalize_math_text(mistake.get('correct_answer'))
            })

        if not grounded_mistakes and not weak_points:
            return [], None

        prompt = f"""你是一位严谨的中学教辅出题老师，请根据学生真实错题生成“举一反三”练习题。

科目：{normalize_math_text(subject) or '未知科目'}
薄弱点：
{json.dumps(weak_points, ensure_ascii=False)}

真实错题：
{json.dumps(grounded_mistakes, ensure_ascii=False)}

要求：
1. 只输出 JSON，不要 markdown，不要解释文字。
2. 练习题必须围绕这些真实错题的考点和错误类型，不能泛泛而谈。
3. 生成 3-6 道题，尽量覆盖不同错题。
4. 题型仅允许：choice、fill、large。
5. 选择题必须给 4 个选项，每个选项格式为 {{"label":"A","text":"选项内容"}}。
6. 填空题和大题的 options 必须返回空数组。
7. large 题需要给出 steps，其他题型 steps 返回空数组。
8. answer、explanation 必须清晰、可直接展示。
9. difficulty 只允许 easy、medium、hard。
10. 使用纯文本，不要输出 LaTeX 包裹符号。

返回格式：
{{
  "practice_questions": [
    {{
      "question": "题目内容",
      "type": "choice",
      "options": [
        {{"label": "A", "text": "选项A"}},
        {{"label": "B", "text": "选项B"}},
        {{"label": "C", "text": "选项C"}},
        {{"label": "D", "text": "选项D"}}
      ],
      "answer": "A",
      "explanation": "解析",
      "difficulty": "medium",
      "steps": []
    }}
  ]
}}"""

        response = zhipu_client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": prompt}]
        )

        parsed = parse_model_json(response.choices[0].message.content)
        practice_questions = parsed.get('practice_questions', []) if isinstance(parsed, dict) else []
        return practice_questions, None
    except Exception as e:
        print(f"生成举一反三练习题失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return None, f"生成练习题失败: {str(e)}"


def save_followup_practice_questions(user_id, subject, practice_questions):
    """保存举一反三练习题。"""
    try:
        if not practice_questions:
            return 0

        saved_count = 0
        normalized_subject = normalize_math_text(subject) or '未知科目'

        for item in practice_questions:
            if not isinstance(item, dict):
                continue

            question_text = normalize_math_text(item.get('question'))
            answer_text = normalize_math_text(item.get('answer'))
            if not question_text or not answer_text:
                continue

            raw_type = normalize_math_text(item.get('type', 'choice')).lower()
            if raw_type not in {'choice', 'fill', 'large'}:
                raw_type = 'choice'

            raw_options = item.get('options', [])
            options = []
            if raw_type == 'choice' and isinstance(raw_options, list):
                for option in raw_options[:4]:
                    if isinstance(option, dict):
                        label = normalize_math_text(option.get('label'))
                        text = normalize_math_text(option.get('text'))
                    else:
                        label = ''
                        text = normalize_math_text(option)
                    if not text:
                        continue
                    options.append({
                        'label': label or chr(ord('A') + len(options)),
                        'text': text
                    })

            raw_steps = item.get('steps', [])
            if not isinstance(raw_steps, list):
                raw_steps = [raw_steps] if raw_steps else []
            steps = [normalize_math_text(step) for step in raw_steps if normalize_math_text(step)]

            difficulty = normalize_math_text(item.get('difficulty', 'medium')).lower()
            if difficulty not in {'easy', 'medium', 'hard'}:
                difficulty = 'medium'

            practice = PracticeQuestion(
                user_id=user_id,
                subject=normalized_subject,
                question=question_text,
                question_type=raw_type,
                options=options if raw_type == 'choice' else [],
                answer=answer_text,
                explanation=normalize_math_text(item.get('explanation')),
                difficulty=difficulty,
                steps=steps if raw_type == 'large' else [],
                is_mastered=False
            )
            db.session.add(practice)
            saved_count += 1

        if saved_count:
            db.session.commit()
        return saved_count
    except Exception as e:
        db.session.rollback()
        print(f"保存举一反三练习题失败: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return 0


def image_file_to_data_url(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp'
    }
    mime_type = mime_map.get(ext, 'image/jpeg')
    with open(file_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded}"


def sanitize_review_result(raw_result, outline_questions=None):
    """统一清洗试卷分析结果，确保前端展示和错题入库复用同一份数据。"""
    if not isinstance(raw_result, dict):
        raw_result = {}

    subject = normalize_math_text(raw_result.get('subject')) or '未知科目'
    weak_points = _normalize_string_list(raw_result.get('weak_points', []))
    suggestions = _normalize_string_list(raw_result.get('suggestions', []))

    cleaned_mistakes = []
    for index, item in enumerate(raw_result.get('mistakes', []), start=1):
        if not isinstance(item, dict):
            continue

        question_no_from_outline, raw_question_no, matched_outline_id = _choose_outline_question_no(
            item,
            outline_questions or [],
            index
        )
        question_no = simplify_question_no(question_no_from_outline, index)
        question_text = normalize_math_text(item.get('question_text') or item.get('question'))
        user_answer = normalize_math_text(item.get('user_answer'))
        correct_answer = normalize_math_text(item.get('correct_answer'))
        explanation = normalize_math_text(item.get('explanation'))
        error_text = normalize_math_text(item.get('error_text') or item.get('error_reason'))
        stem_summary = normalize_math_text(item.get('stem_summary')) or _build_stem_summary(question_text)
        question_type = normalize_math_text(item.get('question_type')) or 'unknown'
        knowledge_points = _normalize_string_list(item.get('knowledge_points', []))

        if answers_mean_equivalent(user_answer, correct_answer):
            continue

        if not error_text:
            if user_answer and correct_answer:
                error_text = f"学生作答“{user_answer}”与正确答案“{correct_answer}”不一致"
            elif explanation:
                error_text = explanation[:40] + ('...' if len(explanation) > 40 else '')
            else:
                error_text = '该题存在作答错误'

        student_error_text = make_student_friendly_error_text(
            question_type,
            stem_summary,
            error_text,
            user_answer,
            correct_answer,
            explanation
        )

        if not question_text:
            question_text = f"原卷{question_no}题目文字识别不清，请结合原试卷查看。"

        cleaned_mistakes.append({
            'outline_id': matched_outline_id,
            'question_no': question_no,
            'raw_question_no': raw_question_no,
            'question_type': question_type,
            'stem_summary': stem_summary,
            'error_text': student_error_text,
            'raw_error_text': error_text,
            'question_text': question_text,
            'display_question': build_display_question(question_no, question_text),
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'explanation': explanation,
            'knowledge_points': knowledge_points
        })

    return {
        'subject': subject,
        'weak_points': weak_points,
        'suggestions': suggestions,
        'mistakes': cleaned_mistakes
    }


def build_exam_marks(mistakes):
    marks = []
    for mistake in mistakes:
        question_type = normalize_math_text(mistake.get('question_type', 'unknown')).lower()
        if '选择' in question_type:
            question_type = 'choice'
        elif '填空' in question_type:
            question_type = 'fill'
        elif '大题' in question_type or '解答' in question_type or '综合' in question_type:
            question_type = 'large'

        stem_summary = normalize_math_text(mistake.get('stem_summary', ''))
        correct_answer = normalize_math_text(mistake.get('correct_answer'))
        thinking_hint = _extract_short_thinking_hint(mistake.get('explanation'))
        error_text = normalize_math_text(mistake.get('error_text', '该题存在作答错误'))
        display_text = error_text

        if question_type in {'choice', 'fill'}:
            display_text = f"正确答案：{correct_answer}" if correct_answer else display_text
        elif question_type == 'large' and correct_answer:
            display_text = f"关键结果：{correct_answer}"

        if len(display_text) > 36:
            display_text = f"{display_text[:36].rstrip()}..."

        marks.append({
            'question_no': simplify_question_no(mistake.get('question_no', '未知题号')),
            'question_type': question_type,
            'stem_summary': stem_summary,
            'error_text': display_text,
            'correct_answer': correct_answer,
            'thinking_hint': thinking_hint
        })
    return marks


def extract_question_outline_with_vision(base64_data):
    """先抽取试卷题目轮廓，给正式批改提供稳定题号锚点。"""
    try:
        image_url = _prepare_image_url(base64_data)
        prompt = """你是一个极度严谨的试卷结构分析助手，请只做题目定位，不要批改。

请先阅读整张试卷，并严格返回 JSON：
{
    "subject": "科目名称",
    "questions": [
        {
            "question_no": "精确题号，例如：选择题第3题、第2大题(1)",
            "question_type": "choice/fill/short/large/other",
            "stem_summary": "不超过20字的题干摘要"
        }
    ]
}

规则：
1. 题号必须尽量贴近原卷层级，例如“大题+小题”。
2. 如果同一大题下有多个小题、填空或选择小问，必须分别写成“第3大题(1)”“第3大题(2)”这类格式。
3. 只输出能明确识别的题目，不要臆造。
4. `stem_summary` 必须简洁，不要抄整题。"""

        response = zhipu_client.chat.completions.create(
            model="glm-4v-plus",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        )

        outline = parse_model_json(response.choices[0].message.content)
        if not isinstance(outline, dict):
            return {'subject': '', 'questions': []}, None

        questions = []
        for index, item in enumerate(outline.get('questions', []), start=1):
            if not isinstance(item, dict):
                continue
            question_no = _normalize_question_no(item.get('question_no'), index)
            questions.append({
                'outline_id': index,
                'question_no': question_no,
                'question_type': normalize_math_text(item.get('question_type')) or 'other',
                'stem_summary': normalize_math_text(item.get('stem_summary'))
            })

        return {
            'subject': normalize_math_text(outline.get('subject')),
            'questions': questions
        }, None
    except Exception as e:
        error_msg = f"试卷题目轮廓提取失败: {str(e)}"
        print(error_msg)
        print(f"错误详情: {traceback.format_exc()}")
        return None, error_msg

def analyze_exam_paper_with_vision(base64_data):
    """Analyze exam paper image and return a normalized review result."""
    try:
        print("Starting GLM-4V exam analysis...")
        start_time = time.time()
        image_url = _prepare_image_url(base64_data)

        outline, outline_error = extract_question_outline_with_vision(base64_data)
        if outline_error:
            print(outline_error)
            outline = {'subject': '', 'questions': []}

        content = request_exam_analysis(image_url, outline, strict_mode=False)

        elapsed_time = time.time() - start_time
        print(f"GLM-4V exam analysis finished in {elapsed_time:.2f}s")
        print(f"API response preview: {content[:200]}...")

        try:
            parsed = parse_model_json(content)
        except json.JSONDecodeError as first_error:
            print(f"First-pass JSON parse failed, retrying with strict prompt: {first_error}")
            retry_content = request_exam_analysis(image_url, outline, strict_mode=True)
            print(f"Strict retry response preview: {retry_content[:200]}...")
            parsed = parse_model_json(retry_content)

        result = sanitize_review_result(parsed, outline.get('questions', []))
        if result.get('subject') == '未知科目':
            outline_subject = normalize_math_text(outline.get('subject'))
            if outline_subject:
                result['subject'] = outline_subject
        return result, None

    except Exception as e:
        error_msg = f"Vision exam analysis failed: {str(e)}"
        print(error_msg)
        print(f"Traceback: {traceback.format_exc()}")
        return None, error_msg


def extract_mistakes_with_vision(base64_data, subject, marks_info):
    """Compatibility helper for re-extracting mistake details from known marks."""
    try:
        print(f"Starting mistake detail extraction for {subject}...")
        start_time = time.time()
        image_url = _prepare_image_url(base64_data)

        prompt = f"""You are a structured extraction assistant.
The uploaded image is a {subject} exam paper.
Known wrong-question markers:
{json.dumps(marks_info, ensure_ascii=False)}

Rules:
1. Extract exactly one result for each known marker. Do not add new mistakes.
2. original_question_no must reuse the provided question number.
3. question must be the full wrong-question content from the paper, including the concrete conditions, expressions, sub-question text, options or blanks when visible. Do not return only a section title or a generic heading like "solve the following equation".
4. user_answer must be the student's answer, not the correct answer.
5. Use plain readable math text only. Do not output LaTeX wrappers.

Return JSON only:
{{
  "mistakes": [
    {{
      "original_question_no": "question number",
      "question": "question text",
      "user_answer": "student answer",
      "correct_answer": "correct answer",
      "explanation": "explanation",
      "knowledge_points": ["kp1", "kp2"]
    }}
  ]
}}"""

        response = zhipu_client.chat.completions.create(
            model="glm-4v-plus",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        )

        elapsed_time = time.time() - start_time
        print(f"Mistake extraction finished in {elapsed_time:.2f}s")

        content = response.choices[0].message.content
        mistakes_dict = parse_model_json(content)
        cleaned = sanitize_review_result({
            'subject': subject,
            'weak_points': [],
            'suggestions': [],
            'mistakes': mistakes_dict.get('mistakes', [])
        })
        mistakes_list = cleaned.get('mistakes', [])
        print(f"Extracted {len(mistakes_list)} mistakes")
        return mistakes_list, None

    except Exception as e:
        print(f"Mistake extraction failed: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return None, f"Mistake extraction failed: {str(e)}"


def generate_parent_advice(mistakes, practice_questions):
    """
    根据学生最近的错题和练习题情况，生成家长辅导话术和学习周报总结
    """
    try:
        # 如果没有数据，返回默认值
        if not mistakes and not practice_questions:
            return {
                "tutoring_advice": "孩子最近没有错题记录，继续保持良好的学习习惯吧！如果遇到难题，建议多鼓励、少批评，陪伴孩子一起探索答案。",
                "summary": "本周学习状态平稳，没有发现明显的薄弱环节。",
                "suggestion": "建议下周可以适当增加一些拓展性阅读或趣味练习，激发学习兴趣。"
            }

        # 整理错题信息
        mistake_subjects = {}
        error_types = {}
        for m in mistakes:
            subject = m.subject or "综合"
            mistake_subjects[subject] = mistake_subjects.get(subject, 0) + 1
            e_type = m.error_type if getattr(m, 'error_type', None) else '未归类'
            error_types[e_type] = error_types.get(e_type, 0) + 1
            
        mistake_summary = ", ".join([f"{k}错了{v}题" for k, v in mistake_subjects.items()])
        error_type_summary = ", ".join([f"{k}原因{v}题" for k, v in error_types.items()])
        
        prompt = f"""你是一个深谙教育心理学、懂孩子也懂家长的“AI家长辅导专家”。
已知孩子近期学习情况如下：
- 错题情况：{mistake_summary}（共 {len(mistakes)} 道错题）
- 错题归因分析：{error_type_summary}
- 练习题情况：共完成了 {len(practice_questions)} 道举一反三练习题

请根据以上真实的错题归因情况，为家长生成一份【辅导锦囊】，并严格按照下方JSON格式返回：

{{
    "tutoring_advice": "提供一段充满情绪价值的辅导话术建议。例如：'孩子这道题错了，不要发火，根据分析他主要是在概念上有些模糊，建议您...'（字数100字左右，语气温和、有共情力）",
    "summary": "一句话总结孩子本周/本月的学习表现，指出核心问题。例如：'本周主要在计算错误上丢分较多，但学习态度积极。'",
    "suggestion": "给出一条针对性的下周学习建议。例如：'针对计算粗心问题，下周建议每天抽出10分钟进行口算专项练习。'"
}}
"""
        response = zhipu_client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.choices[0].message.content
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        json_match = re.search(json_pattern, content)
        json_str = json_match.group(1) if json_match else content.strip()
        
        try:
            result = json.loads(json_str)
            return result
        except Exception:
            return {
                "tutoring_advice": "辅导孩子时请保持耐心，多用鼓励代替指责。错题是查漏补缺的好机会，建议您和孩子一起分析错误原因，而不是只看对错。",
                "summary": f"近期共发现 {len(mistakes)} 道错题，主要集中在 {list(mistake_subjects.keys())[0] if mistake_subjects else '各科'}。",
                "suggestion": "建议下周重点复习错题本上的题目，做到举一反三。"
            }
            
    except Exception as e:
        print(f"生成家长建议失败: {str(e)}")
        return {
            "tutoring_advice": "辅导孩子时请保持耐心，多用鼓励代替指责。错题是查漏补缺的好机会，建议您和孩子一起分析错误原因，而不是只看对错。",
            "summary": "近期学习情况已记录，系统正在持续跟进中。",
            "suggestion": "建议多加复习巩固，保持良好的学习习惯。"
        }

def save_base64_image(base64_data, username):
    """保存Base64图像到文件系统"""
    try:
        # 创建存储目录
        upload_dir = os.path.join('static', 'uploads', 'exam_papers')
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
        return f"/static/uploads/exam_papers/{filename}"
    except Exception as e:
        print(f"保存图片失败: {e}")
        return None
