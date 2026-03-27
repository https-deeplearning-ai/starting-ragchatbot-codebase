def detect_language(text: str) -> str:
    """
    检测文本语言，返回 'zh' 或 'en'

    Args:
        text: 要检测的文本

    Returns:
        'zh' 表示中文，'en' 表示英文
    """
    if not text or not text.strip():
        return 'en'

    # 统计中文字符数量
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    total_chars = len(text.strip())

    # 如果中文字符占比超过30%，判定为中文
    if total_chars > 0 and chinese_chars / total_chars > 0.3:
        return 'zh'
    return 'en'
