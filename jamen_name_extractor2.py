import logging
import sys
import time

import jamen_utils
from jamen_cutter import JamenCutter

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(filename)s: %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


class JamenNameExtractor(JamenCutter):
    _chinese_family_names = {}
    _chinese_given_names = {}
    _chinese_name_prefixes = {}
    _chinese_name_suffixes = {}

    def __init__(self):
        JamenCutter.__init__(self)
        self._load_dict('dict\\chinese_family_names.dict', self._chinese_family_names)
        self._load_dict('dict\\chinese_given_names.dict', self._chinese_given_names)
        self._load_dict('dict\\chinese_name_prefixes.dict', self._chinese_name_prefixes)
        self._load_dict('dict\\chinese_name_suffixes.dict', self._chinese_name_suffixes)

    def _extract(self, sentence):
        prev, curr = None, None
        for word, prop in self._cutter.cut_with_prop(sentence):
            curr = word, prop

    def _cut_chn(self, clip, bond=False):
        name = ''
        for word, prop in JamenCutter._cut_chn(self, clip, bond):
            if not name and prop == 'x':
                if (word in self._chinese_name_prefixes
                        or word in self._chinese_family_names
                        or word in self._chinese_given_names):
                    name += word
            elif name and word in self._chinese_given_names or word in self._chinese_name_suffixes:
                name += word
            yield word, prop

    def _extra_chinese_names(self, clip):
        """
        从中文句子中提取中文名字
        :param clip: 句子
        :return:
        """
        n = len(clip)
        for i in range(0, n - 1):
            family_name = clip[i:i + 1]
            family_name_weight = self._chinese_family_names.get(family_name, -1)
            if family_name_weight < 0:
                continue
            elif family_name_weight == 1:
                for l in range(1, min(3, n - i)):
                    given_name = clip[i + 1:i + 1 + l]
                    given_name_weight = self._chinese_given_names.get(given_name, -1)
                    if given_name_weight < 0:
                        break
                    elif given_name_weight > 0:
                        yield family_name + given_name

            # 复姓
            family_name = clip[i:i + 2]
            family_name_weight = self._chinese_family_names.get(family_name, -1)
            if family_name_weight < 0:
                continue
            elif family_name_weight == 1:
                for l in range(1, min(3, n - i - 1)):
                    given_name = clip[i + 2:i + 2 + l]
                    given_name_weight = self._chinese_given_names.get(given_name, -1)
                    if given_name_weight < 0:
                        break
                    elif given_name_weight > 0:
                        yield family_name + given_name

    def extract(self, sentence):
        names = {}
        for name in self._extract(sentence):
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
    book_path = 'res/材料帝国1.txt'
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
    print("/".join(extractor.cut(jamen_utils.load_text(book_path))))

    # names = {}
    # for name, count in extractor.extract(jamen_utils.load_text(book_path)):
    #     print(name, count)
    #
    # end_time = time.perf_counter()
    # logging.info(f"time cost: {end_time - begin_time}")
