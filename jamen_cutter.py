import hashlib
import logging
import marshal
import os
import re
import sys
import time
from math import log

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
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 6

    _dict = {}  # 完整字典
    _total_weight = 0
    _chinese_family_names = {}
    _chinese_given_names = {}
    _chinese_name_prefixes = {}
    _chinese_name_suffixes = {}
    _japanese_names = {}
    _english_names = {}

    _not_included_regex = re.compile("")
    """未收录词正则式"""

    def __init__(self):
        self._load_dicts_with_cache([
            'dict/jieba_without_nr.dict',
            'dict/chinese.dict',
            'dict/chinese_regions.dict',
            'dict/world_countries.dict',
            'dict/chinese_colleges.dict',
            'dict/chinese_stop_words.dict',
        ], self._dict)

        for v in self._dict.values():
            self._total_weight += v[0]
        logging.info(f"dict words count: {len(self._dict)}")

        self._load_dicts_with_cache(['dict/japanese_names.dict'], self._japanese_names)
        self._load_dicts_with_cache(['dict/english_names.dict'], self._english_names)
        self._load_dicts_with_cache(['dict/chinese_family_names.dict'], self._chinese_family_names)
        self._load_dicts_with_cache(['dict/chinese_given_names.dict'], self._chinese_given_names)
        self._load_dicts_with_cache(['dict/chinese_name_prefixes.dict'], self._chinese_name_prefixes)
        self._load_dicts_with_cache(['dict/chinese_name_suffixes.dict'], self._chinese_name_suffixes)
        self.__load_not_included_regex('data/not_included_regexps.txt')

    def _load_dicts_with_cache(self, dict_path_list, dict, with_cache=True):
        cache_file_path = ''
        need_update = False

        if with_cache:
            cache_dir = "tmp"
            jamen_utils.makesure_dir(cache_dir)
            cache_file_name = hashlib.sha1((",".join(dict_path_list)).encode('utf-8')).hexdigest()
            cache_file_path = os.path.join(cache_dir, cache_file_name)

            if not os.path.exists(cache_file_path):
                need_update = True
            else:
                cache_modify_time = os.path.getmtime(cache_file_path)
                for dict_path in dict_path_list:
                    modify_time = os.path.getmtime(dict_path)
                    if modify_time > cache_modify_time:
                        need_update = True
                        break

        if with_cache and not need_update:
            with open(cache_file_path, 'rb') as file:
                dict.update(marshal.load(file))
                logging.debug(f"load dict from cache '{cache_file_path}'")
        else:
            for dict_path in dict_path_list:
                self._load_dict(dict_path, dict)

        if with_cache and need_update:
            with open(cache_file_path, 'wb') as file:
                marshal.dump(dict, file)
                logging.debug(f"dump dict into cache '{cache_file_path}'")

    def _load_dict(self, dict_path, dict):
        logging.debug(f"load dict['{dict_path}']...")
        with open(dict_path, 'r', encoding='UTF-8') as f:
            for line in [l.strip() for l in f if l.strip()]:
                if line[:1] == '#':
                    # 忽略注释
                    continue

                word, weight, prop = (line + '  ').split(' ')[:3]
                weight = int(weight) if weight else 1
                if word not in dict:
                    dict[word] = weight, prop

                # 构建前缀词典
                for i in range(1, len(line)):
                    frag = word[:i]
                    if frag not in dict:
                        dict[frag] = 0, ''  # 前缀词权重为0
        logging.debug(f"load dict['{dict_path}'] done, size: {len(dict)} ")

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
        self._not_included_regex = re.compile(f"{reg_str}", re.U)
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
                yield clip, 'sym'

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
                yield frag, route[i][4]
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

                # 普通词
                word_weight, word_prop = self._dict.get(frag, (-1, ''))
                if j == i + 1 or word_weight > 0:
                    ends.append((j - 1, max(0, word_weight), word_prop))
                    continue

                chinese_name_weight = self.match_chinese_name(frag)
                if chinese_name_weight > 0:
                    ends.append((j - 1, chinese_name_weight, 'nr'))
                    continue

                japanese_name_weight, prop = self._japanese_names.get(frag, (-1, ''))
                if japanese_name_weight > 0:
                    ends.append((j - 1, japanese_name_weight, 'nr'))
                    continue

                english_name_weight, prop = self._english_names.get(frag, (-1, ''))
                if english_name_weight > 0:
                    ends.append((j - 1, english_name_weight, 'nr'))
                    continue

                if word_weight < 0 and chinese_name_weight < 0 and japanese_name_weight < 0 and english_name_weight < 0:
                    break
        return dag

    # noinspection PyMethodMayBeStatic
    def _calc_route(self, clip, dag):
        route = {}
        n = len(dag)
        total_log_weight = log(self._total_weight)
        route[n] = (0, 0, '', 0, '')  # 方便计算时不溢出
        route_debug = {}
        for i in range(n - 1, -1, -1):
            # jieba的处理参考
            # route[idx] = max((log(self.FREQ.get(sentence[idx:x + 1]) or 1) -
            #                   logtotal + route[x + 1][0], x) for x in DAG[idx])

            # 动态规划，用词长做频度
            # route[i] = max(((k - i + 1) + route[k + 1][0], k, clip[i:k + 1], weight, prop)
            #                for k, weight, prop in dag[i])

            # 向jieba妥协了
            route[i] = max((log(weight or 1) - total_log_weight + route[k + 1][0], k, clip[i:k + 1], weight, prop)
                           for k, weight, prop in dag[i])

            route_debug[i] = [(log(weight or 1) - total_log_weight + route[k + 1][0], k, clip[i:k + 1],
                               log(weight or 1) - total_log_weight, prop) for k, weight, prop in dag[i]]

        del (route[n])
        return route

    def match_chinese_name(self, str):
        if len(str) < 2:
            return -1

        max_weight = -1
        n = len(str)
        for name_prefix, name_prefix_weight in self._match_prefix_dict(str, self._chinese_name_prefixes, 0):
            i = len(name_prefix)

            for family_name, family_name_weight in self._match_prefix_dict(str, self._chinese_family_names, i):
                j = i + len(family_name)
                if j == n:
                    max_weight = max(max_weight, family_name_weight)
                    continue
                elif family_name_weight == 0:
                    continue
                elif name_prefix and family_name:
                    continue

                for given_name, given_name_weight in self._match_prefix_dict(str, self._chinese_given_names, j):
                    if name_prefix and not family_name and len(given_name) > 1:
                        continue  # 前缀通常带单姓或单名或直接带后缀，不会带双名

                    k = j + len(given_name)
                    if k == n:
                        max_weight = max(max_weight, given_name_weight)
                        continue
                    elif given_name_weight == 0:
                        continue

                    if name_prefix and family_name:
                        continue  # 超过两个部分则已经是较完整名字，无须再带后缀
                    elif given_name:
                        continue  # 有名了也无须带后缀
                    else:
                        for name_suffix, suffix_weight in self._match_prefix_dict(str, self._chinese_name_suffixes, k):
                            m = k + len(name_suffix)
                            if m == n:
                                max_weight = max(max_weight, suffix_weight)

        if max_weight > 0:
            # 适当提高一点姓名的权重
            max_weight = max(max_weight, 10)
        return max_weight

    @staticmethod
    def _match_prefix_dict(str, prefix_dict, begin=0):
        for end in range(begin + 1, len(str) + 1):
            tmp = str[begin:end]
            x, prop = prefix_dict.get(tmp, (-1, ''))
            if x >= 0:
                yield tmp, x
            if x < 0:
                break
        yield '', 1

    @staticmethod
    def list_sub_words(clip, min_length=2, max_length=7):
        """
        从一个断句中列举出所有词的组合
        :param max_length: 最短词长
        :param min_length: 最长词长
        :param clip: 要切分的句子
        :return: 所有子词组合的迭代器
        """
        n = len(clip)
        for begin in range(0, n - min_length + 1):
            for end in range(begin + min_length,
                             begin + min(n - begin, max_length) + 1):
                yield clip[begin:end]

    def extract_names(self, sentence):
        """
        提炼姓名
        :param sentence:
        :return:
        """
        names = {}
        for tag, prop in self.cut_with_prop(sentence):
            if prop == 'nr':
                names[tag] = names.get(tag, 0) + 1
                pass
            # elif prop == 'x' and len(tag) >= 2:
            #     names[tag] = names.get(tag, 0) + 1

        # 剔除一些跟高频名字粘结的低频名字，比如“秦海”与“秦海道”
        for name, count in sorted(names.items(), key=lambda x: len(x[0]), reverse=True):
            for n in range(len(name) - 1, 1, -1):
                for b in range(0, len(name) - n + 1):
                    sub_name = name[b:b + n]
                    sub_name_count = names.get(sub_name, 0)
                    if sub_name_count * 0.2 > count:
                        names[name] = 0
                        names[sub_name] = sub_name_count + count

        return filter(lambda x: x[1] > 0, sorted(names.items(), key=lambda x: x[1], reverse=True))

    def extract_names2(self, sentence):
        reg1 = re.compile('([\u4e00-\u9fa5，]*)[问说道]：', re.U)
        reg2 = re.compile('”([\u4e00-\u9fa5]+)', re.U)

        words = {}
        for line in [line.strip() for line in re.split('\n|，', sentence) if line]:
            result1 = reg1.search(line)
            if result1:
                for word in self.list_sub_words(result1.group(1)):
                    for w in self._not_included_regex.split(word):
                        words[w] = words.get(w, 0) + 1
            result2 = reg2.search(line)
            if result2:
                for word in self.list_sub_words(result2.group(1)):
                    for w in self._not_included_regex.split(word):
                        words[w] = words.get(w, 0) + 1

        self._zip_dict(words)
        for k, v in [(k, v) for k, v in sorted(words.items(), key=lambda x: x[1], reverse=True)
                     if len(k) > 1 and v > 1]:
            yield k, v

    def _zip_dict(self, dict):
        for key, count in [(k, c) for k, c in sorted(dict.items(), key=lambda x: len(x[0]), reverse=True)
                           if len(k) > 2]:
            for sub_key in self.list_sub_words(key, 2, len(key) - 1):
                sub_key_count = dict.get(sub_key, 0)
                if count == sub_key_count and sub_key_count > 0:
                    dict[sub_key] = 0


def pre_extract_names(self, sentence):
    _re_name = re.compile(
        "[对向][着]?([^他她它你我]{2,3}?|[A-Za-z]+)(([发询反]?问道)|([回]?答道)|([说喊吼]?道))[^\u4E00-\u9FD5]",
        re.U)
    for line in [line.strip() for line in sentence.split('\n') if line]:
        match_result = _re_name.search(line)
        if match_result:
            print(match_result.group(1) + "\t" + match_result.group(0))


if __name__ == '__main__':
    begin_time = time.perf_counter()
    cutter = JamenCutter()
    # book_path = 'res/test_book.txt'
    # book_path = 'res/材料帝国1.txt'
    book_path = 'res/材料帝国.txt'
    # book_path = 'D:/OneDrive/Books/临高启明.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\庆余年.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\侯卫东官场笔记.txt'
    # book_path = 'D:\\OneDrive\\Books\\重生之官路商途原稿加最好的蛇足续版.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\兽血沸腾.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\将夜.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\流氓高手II.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\紫川.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\活色生香.txt'
    # book_path = 'E:\\BaiduCloud\\Books\\弹痕.txt'

    # print("/".join(cutter.cut(jamen_utils.load_text(book_path))))
    # print("/".join(cutter.cut('秦海诧异道')))
    # print("/".join(cutter.cut('秦明华一上车')))
    # print("/".join(cutter.cut('秦海能够让')))
    # print("/".join(cutter.cut('秦海能够让陈贺千都感到佩服')))
    # print("/".join(cutter.cut('宁厂长上街去吗')))
    # print("/".join(cutter.cut('翟建国是有备而来')))
    # print("/".join(cutter.cut('路边一位戴着眼镜的文化人')))
    # print("/".join(cutter.cut('路边一位戴着眼镜蛇的文化人')))
    # print("/".join(cutter.cut('着眼镜')))
    # print("/".join(cutter.cut('柴培德道：“像韦宝林这种没有能力、光会吹牛的干部，我早就想动一动了。”')))
    # print("/".join(cutter.cut('徐扬笑道：“柴市长，您有没有听过老百姓是如何评价这些干部的？”')))
    # print("/".join(cutter.cut('发出呛哴哴的金属撞击声')))
    # print("/".join(cutter.cut('我这车正好能坐下四个人')))
    # print("/".join(cutter.cut('周工真的不想')))
    # print("/".join(cutter.cut('胖子道')))
    # print("/".join(cutter.cut('年轻人们反驳道')))
    # print("/".join(cutter.cut('当大家的理想一致的时候')))
    # print("/".join([k + v for (k, v) in cutter.cut_with_prop('老刘，你们就照小秦和冷科长的安排去做')]))

    for name, count in cutter.extract_names(jamen_utils.load_text(book_path)):
        print((name, count))

    # cutter.pre_extract_names(jamen_utils.load_text(book_path))

    end_time = time.perf_counter()
    logging.info(f"time cost: {end_time - begin_time}")
