"""
文本阅读
"""


def load_text(text_path):
    try:
        with open(text_path, 'r', encoding='UTF-8') as file:
            return file.read()
    except text_path:
        with open(text_path, 'r', encoding='gb18030', errors='ignore') as file:
            return file.read()
