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
    __re_eng = re.compile("[a-zA-Z_\\-]+", re.U)
    __re_han = re.compile("[\u4E00-\u9FD5]+", re.U)
    MIN_HAN_WORD_LENGTH = 2
    MAX_HAN_WORD_LENGTH = 7

    __extra_stop_words = set()
    """精确停止词，完全相等就算"""
    __stop_regex = re.compile("")
    """停止词正则式"""

    __dict = {}  # 完整字典
    __tags = {}

    def __init__(self):
        self.__load_dict('dict\\chinese.dict')
        self.__load_dict('dict\\chinese_regions.dict')
        self.__load_dict('dict\\world_countries.dict')
        self.__load_extra_stop_words('data/stop_words.txt')
        self.__load_stop_words_regex('data/stop_regexps.txt')
        logging.info(f"stop words count: {len(self.__extra_stop_words)}")

    def __load_dict(self, dict_path):
        logging.debug(f"load dict['{dict_path}']...")
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for word in [l.strip() for l in f if l.strip()]:
                if word[:1] == '#':
                    # 忽略注释
                    continue

                if len(word) > self.MAX_HAN_WORD_LENGTH:
                    continue

                self.__dict[word] = 1

                # 将不完整的词也加入词典，方便搜索
                for i in range(self.MIN_HAN_WORD_LENGTH, len(word)):
                    frag = word[:i]
                    if frag not in self.__dict.keys():
                        self.__dict[frag] = 0  # 不完整的词权重为0
        logging.debug(f"load dict['{dict_path}'] done, size: {len(self.__dict)} ")

    def __load_extra_stop_words(self, dict_path):
        """加载精确停止词字典"""
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for word in [l.strip() for l in f if l.strip()]:
                self.__extra_stop_words.add(word)
                # self.__dict[word] = 1

    def __load_stop_words_regex(self, dict_path):
        """加载模糊停止词正则式"""
        reg_str = ""
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for exp in [l.strip() for l in f if l.strip()]:
                if exp[:1] == '#':
                    # 忽略注释
                    continue

                if len(reg_str) != 0:
                    reg_str += '|'
                reg_str += exp
        # self.__stop_regex = re.compile(f"({reg_str})", re.U)
        self.__stop_regex = re.compile(f"{reg_str}", re.U)

    def analyse(self, sentence):
        logging.info("build tags...")
        self.__build_tags(sentence)
        logging.info("build tags done")

        logging.debug(f"tags count before extract: {len(self.__tags)}")
        self.__remove_low_freq_tags()
        self.__remove_stop_word_tags()
        self.__remove_stop_regexps()
        self.__remove_redundant_tags()
        self.__remove_redundant_tags()
        self.__remove_low_freq_tags()
        logging.debug(f"tags count after extract: {len(self.__tags)}")

    def __build_tags(self, sentence):
        clips = self.__re_block.split(sentence)  # 切分成不包含标点的片段
        for clip in clips:
            if not clip:
                continue

            if self.__re_eng.match(clip):
                # 英文单词，直接入标签
                self.__add_tag(clip)
                continue

            if self.__re_han.match(clip):
                self.__extract_words(clip)

    def __extract_words(self, clip):
        i = 0
        block_length = len(clip)
        while i < block_length:
            step_i = 1

            j = i
            word = None
            while j < block_length:
                step_j = 1

                frags = {}
                for l in range(self.MIN_HAN_WORD_LENGTH, block_length - j + 1):
                    frag = clip[j:j + l]
                    weight = self.__dict.get(frag, -1)
                    if weight < 0:
                        break
                    frags[frag] = weight
                for frag, weight in sorted(frags.items(), key=lambda x: x[1] * 100 + len(x[0]), reverse=True):
                    # 按权重再词长倒序（关键）查找
                    if weight > 0:
                        word = frag
                        break

                if word:
                    # self.__add_tag(word)
                    if j > i:
                        self.__extract_not_included_words(clip[i:j])
                    step_i = j - i + len(word)
                    break

                j += step_j

            if not word:
                self.__extract_not_included_words(clip[i:block_length])
                step_i = block_length - i

            i += step_i

    def __extract_not_included_words(self, clip):
        """
        收集未收录词
        :param clip:
        :return:
        """
        # if len(clip) > 1:
        #     print(str([x for x in self.__stop_regex.split(clip) if x]) + "\t" + clip)
        for frag in self.__stop_regex.split(clip):
            if len(frag) >= self.MIN_HAN_WORD_LENGTH:
                self.__add_tag(frag)

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
        # 去除黏连字
        # 分离：如“秦海”出现100，“秦海道”出现20次，则长的词语便是无效的，频率差一定系数以下可分离，并将长词次数累加到短词上
        tag_counts = sorted(self.__tags.items(), key=lambda x: x[1] * 1000 - len(x[0]), reverse=True)
        for tag, tag_count in tag_counts:
            for sub_tag, begin_pos, end_pos in self.__list_sub_words(tag):
                sub_tag_count = self.__tags.get(sub_tag, 0)
                if tag_count < sub_tag_count * 0.1:
                    # 被粘上的杂词
                    # logging.debug(f"remove longer tag: {tag} into {sub_tag}")
                    self.__remove_tag(tag)
                    self.__set_tag(sub_tag, sub_tag_count + tag_count)
        logging.debug(f"remove redundant tags done, tags: {len(self.__tags)}")

    def __list_sub_words(self, clip):
        """
        从一个断句中列举出所有词的组合
        :param clip:
        :return:
        """
        for begin in range(0, len(clip) - self.MIN_HAN_WORD_LENGTH + 1):
            for end in range(begin + self.MIN_HAN_WORD_LENGTH, len(clip) + 1):
                sub_word = clip[begin:end]
                yield sub_word, begin, end

    def tags(self):
        return self.__tags

    def __add_tag(self, tag):
        if len(tag) >= self.MIN_HAN_WORD_LENGTH:
            self.__tags[tag] = self.__tags.get(tag, 0) + 1

    def __set_tag(self, tag, count):
        self.__tags[tag] = max(0, count)

    def __remove_tag(self, tag):
        self.__tags.pop(tag, None)


if __name__ == '__main__':
    begin_time = time.perf_counter()
    cutter = TagAnalyzer()
    # book_path = 'res/test_book.txt'
    book_path = 'res/材料帝国.txt'
    # book_path = 'res/材料帝国1.txt'
    # book_path = 'D:\\OneDrive\\Books\\临高启明.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\庆余年.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\侯卫东官场笔记.txt'
    # book_path = 'D:\\OneDrive\\Books\\重生之官路商途原稿加最好的蛇足续版.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\兽血沸腾.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\将夜.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\流氓高手II.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\紫川.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\活色生香.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\弹痕.txt'
    try:
        with open(book_path, 'r', encoding='UTF-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        with open(book_path, 'r', encoding='gb18030', errors='ignore') as file:
            content = file.read()
    cutter.analyse(content)
    end_time = time.perf_counter()
    logging.info(f"time cost: {end_time - begin_time}")

    for k, v in sorted(cutter.tags().items(), key=lambda x: x[1])[:10000]:
        print(k, v)
