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
    __re_block = re.compile("([\u4E00-\u9FD5]+|[a-zA-Z0-9_\\-]+)", re.U)
    __re_eng = re.compile("[a-zA-Z_\\-]+", re.U)
    __re_han = re.compile("[\u4E00-\u9FD5]+", re.U)
    MIN_HAN_WORD_LENGTH = 1
    MAX_HAN_WORD_LENGTH = 0xFFFFFFF

    __dict = {}  # 完整字典
    __not_included_regex = re.compile("")
    """未收录词正则式"""
    __tags = {}

    def __init__(self):
        self.__load_dict('dict\\chinese.dict')
        self.__load_dict('dict\\chinese_regions.dict')
        self.__load_dict('dict\\world_countries.dict')
        self.__load_dict('data/stop_words.txt')
        self.__load_not_included_regex('data/not_included_regexps.txt')
        logging.info(f"dict words count: {len(self.__dict)}")

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
        self.__not_included_regex = re.compile(f"({reg_str})", re.U)
        # self.__stop_regex = re.compile(f"{reg_str}", re.U)

    def cut(self, sentence):
        clips = self.__re_block.split(sentence)  # 切分成不包含标点的片段
        for clip in clips:
            if not clip:
                continue

            if self.__re_eng.match(clip):
                # 英文单词，直接入标签
                yield clip
                continue

            if self.__re_han.match(clip):
                for frag in self.__cut_chn(clip, bond=True):
                    yield frag
            else:
                yield clip

    def __cut_chn(self, clip, bond=False):
        """
        将中文句子切分成词
        :param clip: 句子
        :param bond: 是否黏合单字
        :return:
        """
        dag = self.__build_dag(clip)
        route = self.__calc_route(clip, dag)

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
                    for t in self.__cut_bonded(buf):
                        yield t
                    buf = ''
                yield frag
            i = j
        if buf:
            for t in self.__cut_bonded(buf):
                yield t

    def __cut_bonded(self, bonded_word):
        if len(bonded_word) == 1:
            yield bonded_word
        else:
            words = self.__not_included_regex.split(bonded_word)
            for word in words:
                if word:
                    yield word

    def __build_dag(self, clip):
        dag = {}
        n = len(clip)
        for i in range(n):
            ends = []
            dag[i] = ends
            for j in range(i + 1, n + 1):
                frag = clip[i:j]
                frag_weight = self.__dict.get(frag, -1)
                if j == i + 1 or frag_weight > 0:
                    ends.append(j - 1)
                elif frag_weight < 0:
                    break
        return dag

    # noinspection PyMethodMayBeStatic
    def __calc_route(self, clip, dag):
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
