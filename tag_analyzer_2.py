# encoding=utf-8
import logging
import re
import sys
import time

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(filename)s: %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


class TagAnalyzer:
    __re_block = re.compile("([\u4E00-\u9FD5]+|[a-zA-Z0-9_\\-]+)", re.U)
    __re_eng = re.compile("[a-zA-Z0-9_\\-]+", re.U)
    __re_han = re.compile("[\u4E00-\u9FD5]+", re.U)
    MIN_HAN_WORD_LENGTH = 2
    MAX_HAN_WORD_LENGTH = 4

    __extra_stop_words = set()
    """精确停止词，完全相等就算"""
    __stop_regex = re.compile("")
    """停止词正则式"""

    __dict = {}  # 完整字典
    __tags = {}

    def __init__(self):
        self.__load_dict()
        self.__load_extra_stop_words('data/stop_words.txt')
        self.__load_stop_words_regex('data/stop_regexps.txt')
        logging.info(f"stop words count: {len(self.__extra_stop_words)}")

    def __load_dict(self):
        logging.debug("load dict...")
        with open('dict\\dict.txt', 'r', encoding='UTF-8') as f:
            for word in [l.strip() for l in f if l.strip()]:
                if len(word) > self.MAX_HAN_WORD_LENGTH:
                    continue

                self.__dict[word] = 1

                # 将不完整的词也加入词典，方便搜索
                for i in range(self.MIN_HAN_WORD_LENGTH, len(word)):
                    frag = word[:i]
                    if frag not in self.__dict.keys():
                        self.__dict[frag] = 0  # 不完整的词权重为0
        logging.debug(f"load dict done, size: {len(self.__dict)} ")

    def __load_extra_stop_words(self, dict_path):
        """加载精确停止词字典"""
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for word in [l.strip() for l in f if l.strip()]:
                self.__extra_stop_words.add(word)
                self.__dict[word] = 1

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

        logging.debug(f"tags count before extract: {len(self.__tags)}")
        self.__remove_low_freq_tags()
        self.__remove_stop_word_tags()
        self.__remove_stop_regexps()
        self.__remove_redundant_tags()
        self.__remove_low_freq_tags()
        logging.debug(f"tags count after extract: {len(self.__tags)}")

    def __build_tags(self, sentence):
        """
        根据传入内容构造标签
        :param sentence: 内容
        :return:
        """
        blocks = self.__re_block.split(sentence)  # 切分成不包含标点的片段
        for block in blocks:
            if self.__re_eng.match(block):
                # 英文单词，直接入标签
                # self.__add_tag(block)
                pass
            elif self.__re_han.match(block):
                # logging.debug(block)
                i = 0
                n = len(block)
                while i < n:
                    step = 1

                    words = {}
                    sub_word_begin = self.MAX_HAN_WORD_LENGTH
                    for j in range(self.MIN_HAN_WORD_LENGTH, min(n - i, self.MAX_HAN_WORD_LENGTH) + 1):
                        word = block[i:i + j]
                        word_weight = self.__dict.get(word, 0)
                        words[word] = word_weight

                    # 按权重再词长倒序（关键）
                    for word, weight in sorted(words.items(), key=lambda x: x[1] * 10 + len(x[0]), reverse=True):
                        # 优先词典收录词
                        if weight > 0:
                            # self.__add_tag(word)
                            step = len(word)
                            break

                        # 非词典收录词
                        # 需要剔除其中包含的收录词，如“不懂英语”其中包含收录词“英语”，则不应该收录
                        if sub_word_begin == self.MAX_HAN_WORD_LENGTH:
                            # sub_word_begin = self.__find_sub_word(word)[0]
                            sub_word_begin = self.__find_sub_word(
                                block[i:i + min(n - i, len(word) + self.MAX_HAN_WORD_LENGTH - 1)])[0]

                        if sub_word_begin < 0 or len(word) <= sub_word_begin:
                            # 添加未收录词
                            self.__add_tag(word)

                    i += step

    def __remove_low_freq_tags(self):
        """
        移除低频词
        :return:
        """
        logging.debug("remove low freq tags...")
        for tag, count in {k: v for k, v in self.__tags.items()}.items():
            if count <= 1:
                self.__remove_tag(tag)
        logging.debug(f"remove low freq tags done, tags: {len(self.__tags)}")

    def __remove_stop_word_tags(self):
        """
        移除停用词
        :return:
        """
        logging.debug("remove stop word tags...")
        for tag in [key for key in self.__tags.keys()]:
            if tag in self.__extra_stop_words:
                self.__remove_tag(tag)
        logging.debug(f"remove stop word tags done, tags: {len(self.__tags)}")

    def __remove_stop_regexps(self):
        """
        移除停用词
        :return:
        """
        logging.debug("remove stop regexps tags...")
        for tag in [key for key in self.__tags.keys()]:
            if self.__stop_regex.search(tag):
                self.__remove_tag(tag)
        logging.debug(f"remove stop regexps done, tags: {len(self.__tags)}")

    def __remove_redundant_tags(self):
        """
        去除被包含的冗余词
        :return:
        """
        logging.debug("remove redundant tags...")
        # 去除两种形式的冗余
        # 1、吞噬：如“总工程师”出现次数与“工程师”相等，那短词便是无效的，频率差0.95以内可吞噬
        # 2、分离：如“秦海”出现100，“秦海道”出现20次，则长的词语便是无效的，频率差0.5以下可分离
        tag_counts = sorted(self.__tags.items(), key=lambda x: x[1] * 1000 - len(x[0]), reverse=True)
        for tag, tag_count in tag_counts:
            tag_len = len(tag)
            for i in range(0, tag_len - self.MIN_HAN_WORD_LENGTH + 1):
                for l in range(2, min(tag_len, tag_len - i + 1)):
                    sub_tag = tag[i:i + l]
                    sub_tag_count = self.__tags.get(sub_tag, 0)

                    if tag_count < sub_tag_count * 0.15:
                        # 被粘上的杂词
                        # logging.debug(f"remove longer tag: {longer_tag}")
                        self.__remove_tag(tag)
                    else:
                        sub_tag_count -= tag_count
                        self.__set_tag(sub_tag, sub_tag_count)
        logging.debug(f"remove redundant tags done, tags: {len(self.__tags)}")

    def __find_sub_word(self, word):
        for begin in range(1, len(word) - self.MIN_HAN_WORD_LENGTH + 1):
            for end in range(begin + self.MIN_HAN_WORD_LENGTH, len(word) + 1):
                sub_word = word[begin:end]
                sub_weight = self.__dict.get(sub_word, -1)
                if sub_weight > 0:
                    return begin, end
        return -1, 0

    def tags(self):
        return self.__tags

    def __add_tag(self, tag):
        # logging.debug(f"add tag: {tag}")
        self.__tags[tag] = self.__tags.get(tag, 0) + 1

    def __set_tag(self, tag, count):
        # logging.debug(f"set tag: {tag}:{count}")
        self.__tags[tag] = max(0, count)

    def __remove_tag(self, tag):
        # logging.debug(f"remove tag: {tag}")
        self.__tags.pop(tag, None)


if __name__ == '__main__':
    begin_time = time.perf_counter()
    cutter = TagAnalyzer()
    # book_path = 'res/材料帝国.txt'
    # book_path = 'res/材料帝国.txt'
    # book_path = 'D:\\OneDrive\\Books\\临高启明.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\庆余年.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\侯卫东官场笔记.txt'
    # book_path = 'D:\\OneDrive\\Books\\重生之官路商途原稿加最好的蛇足续版.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\兽血沸腾.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\将夜.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\流氓高手II.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\紫川.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\活色生香.txt'
    book_path = 'E:\\BaiduCloud\\Books\\弹痕.txt'
    try:
        with open(book_path, 'r', encoding='UTF-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        with open(book_path, 'r', encoding='gb18030', errors='ignore') as file:
            content = file.read()
    cutter.analyse(content)
    end_time = time.perf_counter()
    logging.info(f"time cost: {end_time - begin_time}")

    for k, v in sorted(cutter.tags().items(), key=lambda x: x[1], reverse=True)[:10000]:
        print(k, v)
