# encoding=utf-8
import logging
import re
import sys
import time

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

MIN_HAN_WORD_LENGTH = 2
MAX_HAN_WORD_LENGTH = 4
re_block = re.compile("([\u4E00-\u9FD5]+|[a-zA-Z0-9_\\-]+)", re.U)
re_eng = re.compile("[a-zA-Z0-9_\\-]+", re.U)
re_han = re.compile("[\u4E00-\u9FD5]+", re.U)


class Tokenizer:
    """
    基于词频分析的简单分词器
    """
    words = {}

    def analyse(self, sentence):
        logging.info("analyse ...")

        blocks = re_block.split(sentence)

        for block in blocks:
            if re_eng.match(block):
                self.add_word(block)
            elif re_han.match(block):
                n = len(block)
                for i in range(n):
                    for l in range(MIN_HAN_WORD_LENGTH, min(n - i, MAX_HAN_WORD_LENGTH) + 1):
                        word = block[i:i + l]
                        self.add_word(word)

        self.extract_words()

    def add_word(self, word):
        logging.debug(f"add word: {word}")
        self.words[word] = self.words.get(word, 0) + 1

    def remove_word(self, word):
        logging.debug(f"remove word: {word}")
        del self.words[word]

    @staticmethod
    def find_redundant(keys):
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

    # 提炼词典，去除冗余的词
    def extract_words(self):
        logging.info("extract_words ...")

        logging.debug(f"word count before extract: {len(self.words)}")
        pre_count = 0
        temp_words = []
        for word, count in sorted(self.words.items(), key=lambda x: x[1] * 1000 - len(x[0]), reverse=True):
            """按词频倒序+词长正序"""
            if pre_count == 0:
                pass
            elif pre_count != count:
                for redundant_word in self.find_redundant(temp_words):
                    self.remove_word(redundant_word)
                temp_words.clear()

            temp_words.append(word)
            pre_count = count

            if count < 2:
                break

        logging.debug(f"word count after extract: {len(self.words)}")


if __name__ == '__main__':
    time_begin = time.perf_counter()

    tokenizer = Tokenizer()
    with open('res/材料帝国1.txt', 'r', encoding='UTF-8') as file:
    # with open('D:\OneDrive\Books\临高启明.txt', 'r', encoding='UTF-8') as file:
        content = file.read()
        tokenizer.analyse(content)

    time_end = time.perf_counter()
    logging.info(f"time cost: {time_end - time_begin}")
    logging.info(sorted(tokenizer.words.items(), key=lambda x: x[1], reverse=True)[:200])
