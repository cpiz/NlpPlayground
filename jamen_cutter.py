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


class JamenCutter:
    _re_block = re.compile("([\u4E00-\u9FD5]+|[a-zA-Z0-9_\\-]+)", re.U)
    _re_eng = re.compile("[a-zA-Z_\\-]+", re.U)
    _re_han = re.compile("[\u4E00-\u9FD5]+", re.U)
    MIN_HAN_WORD_LENGTH = 1
    MAX_HAN_WORD_LENGTH = 0xFFFFFFF

    _dict = {}  # 完整字典
    _not_included_regex = re.compile("")
    """未收录词正则式"""

    def __init__(self):
        self._load_dict('dict\\chinese.dict', self._dict)
        self._load_dict('dict\\chinese_regions.dict', self._dict)
        self._load_dict('dict\\world_countries.dict', self._dict)
        self._load_dict('dict\\chinese_colleges.dict', self._dict)
        self._load_dict('data\\stop_words.txt', self._dict)
        self.__load_not_included_regex('data\\not_included_regexps.txt')
        logging.info(f"dict words count: {len(self._dict)}")

    @staticmethod
    def _load_dict(dict_path, name_dict):
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

    def __load_not_included_regex(self, dict_path):
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
        self._not_included_regex = re.compile(f"({reg_str})", re.U)
        # self.__stop_regex = re.compile(f"{reg_str}", re.U)

    def cut_with_prop(self, sentence):
        clips = self._re_block.split(sentence)  # 切分成不包含标点的片段
        for clip in clips:
            if not clip:
                continue

            if self._re_eng.match(clip):
                # 英文单词，直接入标签
                yield clip, 'eng'
                continue

            if self._re_han.match(clip):
                for frag, prop in self._cut_chn(clip, bond=True):
                    yield frag, prop
            else:
                yield clip, 'x'

    def cut(self, sentence):
        for word, prop in self.cut_with_prop(sentence):
            yield word

    def _cut_chn(self, clip, bond=False):
        """
        将中文句子切分成词
        :param clip: 句子
        :param bond: 是否黏合单字
        :return:
        """
        dag = self._build_dag(clip)
        route = self._calc_route(clip, dag)

        i = 0
        n = len(clip)
        buf = ''
        while i < n:
            j = route[i][1] + 1
            frag = clip[i:j]
            if bond and j == i + 1:
                buf += frag
            else:
                if buf:
                    for t in self._cut_bonded(buf):
                        yield t, 'x'
                    buf = ''
                yield frag, 'word'
            i = j
        if buf:
            for t in self._cut_bonded(buf):
                yield t, 'x'

    def _cut_bonded(self, bonded_word):
        if len(bonded_word) == 1:
            yield bonded_word
        else:
            words = self._not_included_regex.split(bonded_word)
            for word in words:
                if word:
                    yield word

    def _build_dag(self, clip):
        dag = {}
        n = len(clip)
        for i in range(n):
            ends = []
            dag[i] = ends
            for j in range(i + 1, n + 1):
                frag = clip[i:j]
                frag_weight = self._dict.get(frag, -1)
                if j == i + 1 or frag_weight > 0:
                    ends.append(j - 1)
                elif frag_weight < 0:
                    break
        return dag

    # noinspection PyMethodMayBeStatic
    def _calc_route(self, clip, dag):
        route = {}
        n = len(dag)
        route[n] = (0, 0)  # 方便计算时不溢出
        for i in range(n - 1, -1, -1):
            # jieba的处理参考
            # route[idx] = max((log(self.FREQ.get(sentence[idx:x + 1]) or 1) -
            #                   logtotal + route[x + 1][0], x) for x in DAG[idx])

            # 动态规划，用词长做频度
            route[i] = max((-i + route[x + 1][0], x) for x in dag[i])
        del (route[n])
        return route


if __name__ == '__main__':
    begin_time = time.perf_counter()
    cutter = JamenCutter()
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
    print("/".join(cutter.cut(jamen_utils.load_text(book_path))))
    # print("/".join(cutter.cut('当下雨天地面积水分外严重')))
    # print("/".join(cutter.cut('路边一位戴着眼镜蛇的文化人')))
    end_time = time.perf_counter()
    logging.info(f"time cost: {end_time - begin_time}")
