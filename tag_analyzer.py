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
        """加载模糊停止词正则式"""
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
        logging.debug(f"tags count before extract: {len(self.tags)}")
        self.__remove_low_freq_tags()
        self.__remove_stop_word_tags()
        self.__remove_stop_regexps()
        self.__remove_redundant_tags()
        logging.debug(f"tags count after extract: {len(self.tags)}")
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

    def __set_tag(self, tag, count):
        self.tags[tag] = max(0, count)

    def __remove_tag(self, tag):
        # logging.debug(f"remove tag: {tag}")
        # if self.tags[tag]:
        #     del self.tags[tag]
        self.tags.pop(tag, None)

    def __remove_low_freq_tags(self):
        """
        移除低频词
        :return:
        """
        logging.debug("remove low freq tags...")
        for tag, count in {k: v for k, v in self.tags.items() if v}.items():
            if count == 1:
                self.__remove_tag(tag)
        logging.debug(f"remove low freq tags done, tags: {len(self.tags)}")

    def __remove_stop_word_tags(self):
        """
        移除停用词
        :return:
        """
        logging.debug("remove stop word tags...")
        for tag in [key for key in self.tags.keys()]:
            if tag in self.__extra_stop_words:
                self.__remove_tag(tag)
        logging.debug(f"remove stop word tags done, tags: {len(self.tags)}")

    def __remove_stop_regexps(self):
        """
        移除停用词
        :return:
        """
        logging.debug("remove stop regexps tags...")
        for tag in [key for key in self.tags.keys()]:
            if self.__stop_regex.search(tag):
                self.__remove_tag(tag)
        logging.debug(f"remove stop regexps done, tags: {len(self.tags)}")

    def __remove_redundant_tags(self):
        """
        去除被包含的冗余词
        :return:
        """

        logging.debug("remove redundant tags...")
        # 去除两种形式的冗余

        # 1、吞噬：如“总工程师”出现次数与“工程师”相等，那短词便是无效的，频率差0.95以内可吞噬
        # 2、分离：如“秦海”出现100，“秦海道”出现20次，则长的词语便是无效的，频率差0.5以下可分离
        tag_counts = sorted(self.tags.items(), key=lambda x: x[1] * 1000 - len(x[0]), reverse=True)

        comma_tags_list = {}
        for i in range(1, MAX_HAN_WORD_LENGTH + 1):
            comma_tags_list[i] = "," + ",".join(key for key, value in tag_counts if len(key) == i)

        for tag, tag_count in tag_counts:
            for l in range(len(tag) + 1, MAX_HAN_WORD_LENGTH + 1):
                for longer_tag in re.findall(f",([^,]*{tag}[^,]*)", comma_tags_list[l]):  # 前面是否以逗号开头，性能相差3倍
                    if longer_tag == tag:
                        continue
                    longer_cat_count = self.tags.get(longer_tag, 0)
                    if longer_cat_count < tag_count * 0.15:
                        # 被粘上的杂词
                        # logging.debug(f"remove longer tag: {longer_tag}")
                        self.__remove_tag(longer_tag)
                    else:
                        tag_count -= longer_cat_count
                        self.__set_tag(tag, tag_count)
        logging.debug(f"remove redundant tags done, tags: {len(self.tags)}")


if __name__ == '__main__':
    time_begin = time.perf_counter()

    tag_analyzer = TagAnalyzer()
    # book_path = 'res/材料帝国.txt'
    # book_path = 'D:\\OneDrive\\Books\\临高启明.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\庆余年.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\侯卫东官场笔记.txt'
    book_path = 'D:\\OneDrive\\Books\\重生之官路商途原稿加最好的蛇足续版.txt'
    # with open(book_path, 'r', encoding='GBK') as file:
    with open(book_path, 'r', encoding='UTF-8') as file:
        content = file.read()
        tag_analyzer.analyse(content)

    time_end = time.perf_counter()
    logging.info(f"time cost: {time_end - time_begin}")
    # logging.info(sorted(tokenizer.tags.items(), key=lambda x: x[1], reverse=True))
    for k, v in sorted(tag_analyzer.tags.items(), key=lambda x: x[1], reverse=True)[:10000]:
        print(k, v)
