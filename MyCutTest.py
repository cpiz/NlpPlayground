# encoding=utf-8
import logging
import re
import sys
import time

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

MIN_HAN_WORD_LENGTH = 2
MAX_HAN_WORD_LENGTH = 4
re_block = re.compile("([\u4E00-\u9FD5]+|[a-zA-Z0-9_\\-]+)", re.U)
"""连续内容的切分正则"""

re_eng = re.compile("[a-zA-Z0-9_\\-]+", re.U)
re_han = re.compile("[\u4E00-\u9FD5]+", re.U)


class TagAnalyzer:
    """
    基于词频的简单标签提取分析器
    """
    tags = {}

    __extra_stop_words = set()
    """精确停止词，完全相等就算"""

    __stop_regex = re.compile("")
    """停止词正则式"""

    def __init__(self):
        logging.info("load stop words ...")
        self.__load_extra_stop_words('data/stop_words.txt')
        self.__load_stop_words_regex('data/stop_regexps.txt')
        logging.info(f"stop words count: {len(self.__extra_stop_words)}")

    def __load_extra_stop_words(self, dict_path):
        """加载精确停止词字典"""
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for word in [l.strip() for l in f if l.strip()]:
                self.__extra_stop_words.add(word)

    def __load_stop_words_regex(self, dict_path):
        """加载模糊停止词字典"""
        reg_str = ""
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for exp in [l.strip() for l in f if l.strip()]:
                if len(reg_str) != 0:
                    reg_str += '|'
                reg_str += exp
        self.__stop_regex = re.compile(reg_str, re.U)

    def analyse(self, sentence):
        logging.info("build tags...")
        self.__build_tags(sentence)
        logging.info("build tags done")

        logging.info("extract tags...")
        logging.debug(f"tag count before extract: {len(self.tags)}")
        self.__remove_rares_tags()
        self.__remove_stop_tags()
        self.__remove_stop_regexps()
        self.__remove_contained_tags()
        logging.debug(f"tag count after extract: {len(self.tags)}")
        logging.info("extract tags done")

    def __build_tags(self, sentence):
        """
        构造指定内容的标签
        :param sentence: 文本内容
        :return:
        """
        blocks = re_block.split(sentence)  # 切分成不包含标点的片段
        for block in blocks:
            if re_eng.match(block):
                # 英文单词，直接入标签
                self.__add_tag(block)
            elif re_han.match(block):
                n = len(block)
                i = 0
                while i < n:
                    # for i in range(n):
                    for l in range(MIN_HAN_WORD_LENGTH, min(n - i, MAX_HAN_WORD_LENGTH) + 1):
                        # 汉字内容，逐个组合入标签
                        tag = block[i:i + l]

                        # 过滤停止词
                        stop_pos = self.__find_stop_word_(tag)
                        if stop_pos[0] != -1:
                            i += (stop_pos[1] - 1)  # 切换游标到停止词位置，避免重复查找
                            break

                        self.__add_tag(tag)
                    i += 1

    def __find_stop_word_(self, word):
        """
        检查指定词中是否包含停止词
        :param word: 要检查的词
        :return: 找到的停止词的起止位置，没找到返回-1，-1
        """
        tag_len = len(word)
        for a in range(tag_len - 1):
            for b in range(a + 2, tag_len + 1):
                if word[a:b] in self.__extra_stop_words:
                    return a, b
        return -1, -1

    def __add_tag(self, tag):
        # logging.debug(f"add tag: {tag}")
        self.tags[tag] = self.tags.get(tag, 0) + 1

    def __remove_tag(self, tag):
        # logging.debug(f"remove tag: {tag}")
        del self.tags[tag]

    def __remove_rares_tags(self):
        """
        移除独特词
        :return:
        """
        # for tag, count in self.tags.items():
        for tag, count in {k: v for k, v in self.tags.items() if v}.items():
            if count == 1:
                self.__remove_tag(tag)

    def __remove_stop_tags(self):
        """
        移除停用词
        :return:
        """
        for tag in [key for key in self.tags.keys()]:
            if tag in self.__extra_stop_words:
                self.__remove_tag(tag)

    def __remove_stop_regexps(self):
        """
        移除停用词
        :return:
        """
        for tag in [key for key in self.tags.keys()]:
            if self.__stop_regex.search(tag):
                self.__remove_tag(tag)

    def __remove_contained_tags(self):
        """
        去除被包含的冗余词
        :return:
        """

        # 去除两种形式的冗余

        # 1、以长废短：如“总工程师”出现次数与“工程师”相等，那短的词语便是无效的
        # 2、以短废长：如“秦海”出现100，“秦海道”出现20次，则长的词语便是无效的
        # TODO: 待优化，需要增加一定容错读，如0.9置信即可
        pre_count = 0
        temp_words = []
        for tag, count in sorted(self.tags.items(), key=lambda x: x[1] * 1000 - len(x[0]), reverse=True):
            """按词频倒序+词长正序"""
            if pre_count == 0:
                pass
            elif pre_count != count:
                for redundant_word in self.__find_redundant(temp_words):
                    self.__remove_tag(redundant_word)
                temp_words.clear()

            temp_words.append(tag)
            pre_count = count

            if count < 2:
                break

    @staticmethod
    def __find_redundant(keys):
        """
        在列表中查找冗余的词语，冗余即被其他词包含，如“你好”被“你好吗”包含，“你好就是冗余词”
        :param keys: 已按词长排序的列表，短词在前
        :return:
        """
        if len(keys) > 1:
            joined_keys = ",".join(keys)
            pos = 0
            for short_word in keys:
                pos += (len(short_word) + 1)
                if joined_keys.find(short_word, pos) > -1:
                    yield short_word
                    continue

        yield from []


if __name__ == '__main__':
    time_begin = time.perf_counter()

    tokenizer = TagAnalyzer()
    # book_path = 'res/材料帝国.txt'
    # book_path = 'D:\\OneDrive\\Books\\临高启明.txt'
    book_path = 'E:\\BaiduCloud\\Books\\庆余年.txt'
    # with open(book_path, 'r', encoding='UTF-8') as file:
    with open(book_path, 'r', encoding='GBK') as file:
        content = file.read()
        tokenizer.analyse(content)

    time_end = time.perf_counter()
    logging.info(f"time cost: {time_end - time_begin}")
    # logging.info(sorted(tokenizer.tags.items(), key=lambda x: x[1], reverse=True))
    for k, v in sorted(tokenizer.tags.items(), key=lambda x: x[1], reverse=True)[:10000]:
        print(k, v)
