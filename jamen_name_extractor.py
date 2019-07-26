import logging
import re
import sys
import time

import jamen_utils

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(filename)s: %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


class JamenNameExtractor:
    __re_block = re.compile("([\u4E00-\u9FD5]+|[a-zA-Z0-9_\\-]+)", re.U)
    __re_eng = re.compile("[a-zA-Z_\\-]+", re.U)
    __re_han = re.compile("[\u4E00-\u9FD5]+", re.U)
    MIN_HAN_WORD_LENGTH = 1
    MAX_HAN_WORD_LENGTH = 4

    __tags = {}

    __chinese_family_names = {}
    __chinese_given_names = {}
    __chinese_dict = {}
    __chinese_names = {}

    def __init__(self):
        self.__load_dict('dict\\chinese_family_names.dict', self.__chinese_family_names)
        self.__load_dict('dict\\chinese_given_names.dict', self.__chinese_given_names)
        self.__load_dict('dict\\chinese.dict', self.__chinese_dict)

    @staticmethod
    def __load_dict(dict_path, name_dict):
        logging.debug(f"load dict['{dict_path}']...")
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for word in [l.strip() for l in f if l.strip()]:
                if word[:1] == '#':
                    # 忽略注释
                    continue

                name_dict[word] = 1  # 完全匹配次权重为1

                # 构建前缀词典
                for i in range(1, len(word)):
                    frag = word[:i]
                    if frag not in name_dict.keys():
                        name_dict[frag] = 0  # 前缀词权重为0
        logging.debug(f"load dict['{dict_path}'] done, size: {len(name_dict)} ")

    def __extract(self, sentence):
        clips = self.__re_block.split(sentence)  # 切分成不包含标点的片段
        for clip in clips:
            if not clip:
                continue

            if self.__re_eng.match(clip):
                continue

            if self.__re_han.match(clip):
                for name in self.__extra_chinese_names(clip):
                    yield name

    def __extra_chinese_names(self, clip):
        """
        从中文句子中提取中文名字
        :param clip: 句子
        :return:
        """
        n = len(clip)
        for i in range(0, n - 1):
            family_name = clip[i:i + 1]
            family_name_weight = self.__chinese_family_names.get(family_name, -1)
            if family_name_weight < 0:
                continue
            elif family_name_weight == 1:
                for l in range(1, min(3, n - i)):
                    given_name = clip[i + 1:i + 1 + l]
                    given_name_weight = self.__chinese_given_names.get(given_name, -1)
                    if given_name_weight < 0:
                        break
                    elif given_name_weight > 0:
                        yield family_name + given_name

            # 复姓
            family_name = clip[i:i + 2]
            family_name_weight = self.__chinese_family_names.get(family_name, -1)
            if family_name_weight < 0:
                continue
            elif family_name_weight == 1:
                for l in range(1, min(3, n - i - 1)):
                    given_name = clip[i + 2:i + 2 + l]
                    given_name_weight = self.__chinese_given_names.get(given_name, -1)
                    if given_name_weight < 0:
                        break
                    elif given_name_weight > 0:
                        yield family_name + given_name

    def extract(self, sentence):
        names = {}
        for name in self.__extract(sentence):
            names[name] = names.get(name, 0) + 1

        # 过滤中文词
        for name in [x for x in names.keys()]:
            if name in self.__chinese_dict:
                del names[name]

        for name in [x for x in names.keys() if len(x) > 2]:
            name_count = names[name]
            for i in range(0, len(name) - 1):
                frag = name[i:i + 2]
                frag_count = names.get(frag, 0)
                if frag_count <= 0:
                    continue

                if name_count >= frag_count:
                    names[frag] = 0

        for k, v in sorted(names.items(), key=lambda x: x[1], reverse=True):
            yield k, v


if __name__ == '__main__':
    begin_time = time.perf_counter()
    extractor = JamenNameExtractor()
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
    # print("/".join(extractor.extract(jamen_utils.load_text(book_path))))

    names = {}
    for name, count in extractor.extract(jamen_utils.load_text(book_path)):
        print(name, count)

    end_time = time.perf_counter()
    logging.info(f"time cost: {end_time - begin_time}")
