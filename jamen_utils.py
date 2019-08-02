"""
文本阅读
"""
import os


def load_text(text_path):
    try:
        with open(text_path, 'r', encoding='UTF-8') as file:
            return file.read()
    except UnicodeDecodeError:
        with open(text_path, 'r', encoding='gb18030', errors='ignore') as file:
            return file.read()


def makesure_dir(dir_path):
    """
    确保目录存在
    :param dir_path:
    :return:
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
