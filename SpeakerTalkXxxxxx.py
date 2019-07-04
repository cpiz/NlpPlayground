# encoding=utf-8
import logging
import re
import sys
import time

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

re_talk = re.compile("((^|[^\u4E00-\u9FD5a-zA-Z0-9])“(.*?)”.?)", re.U)
# re_talk1 = re.compile("“(.*?)”(.*?[道说])", re.U)
# re_talk2 = re.compile("([^“”]*?[道说][:：]+)“(.*?)”", re.U)

re_talk0 = re.compile("^\\s*“(.*?)”\\s*$", re.U)
"""纯对话行"""

re_talk1 = re.compile("(^|[^\u4E00-\u9FD5a-zA-Z0-9])“(.*?)”([^“”]+)", re.U)
"""话在前，人在后"""

re_talk2 = re.compile("([^“”]+(^|[^\u4E00-\u9FD5a-zA-Z0-9]))“(.*?)”", re.U)
"""人在前，话在后"""


# “王晓晨，原来是你住在对面啊。”宁默倒也认识那姑娘，他用手指了指秦海，说道：“这是秦海，我哥们。他是农机技校毕业的，分到咱们厂里工作，以后就和你住对门了。”

class SpeakTalk:
    speaker = ""
    talk = ""

    def __init__(self, speaker, talk):
        self.speaker = speaker
        self.talk = talk
        logging.debug((speaker, talk))


class Tokenizer:
    talks = []

    def analyse(self, sentence):
        for line in sentence:
            self.talks.extend(self.analyse_line(line))

    @staticmethod
    def analyse_line(line):
        if len(line) == 0:
            return []

        # logging.debug(f"analyse_line: {line}")
        m1 = re_talk1.search(line)
        if m1:
            speak = SpeakTalk(m1.group(3), m1.group(2))
            yield speak

        m2 = re_talk2.search(line)
        if m2:
            speak = SpeakTalk(m2.group(1), m2.group(3))
            yield speak

        m0 = re_talk0.search(line)
        if m0:
            speak = SpeakTalk("", m0.group(1))
            yield speak

        yield


if __name__ == '__main__':
    time_begin = time.perf_counter()

    tokenizer = Tokenizer()
    with open('res/材料帝国1.txt', 'r', encoding='UTF-8') as file:
        content = [x.strip() for x in file.readlines()]
        tokenizer.analyse(content)

    time_end = time.perf_counter()
    logging.info(f"time cost: {time_end - time_begin}")
