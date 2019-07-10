# encoding=utf-8
import logging
import re
import sys
import time

import jieba

from DoubleLinkedNode import DoubleLinkedNode
from tag_analyzer_1 import TagAnalyzer

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

re_word_in_quote = re.compile("(“.*?”)")
re_end_with_noword = re.compile(".*[^\u4E00-\u9FD5a-zA-Z0-9]$")


# re_quote = re.compile("[“”]")
# “王晓晨，原来是你住在对面啊。”宁默倒也认识那姑娘，他用手指了指秦海，说道：“这是秦海，我哥们。他是农机技校毕业的，分到咱们厂里工作，以后就和你住对门了。”

class SpeakerTalk:
    speaker = ""
    """角色名称"""

    talk = ""
    """说话内容"""

    row_num = 0
    """说话内容所在的行号，从第1行开始"""

    def __init__(self, row_num, talk):
        self.row_num = row_num
        self.speaker = ""
        self.talk = talk
        # logging.debug((speaker, talk))

    def __str__(self):
        speaker = self.speaker if self.speaker else None
        return f"row[{self.row_num}]{speaker}: {self.talk}"


class SpeakerTalkAnalyzer:
    tag_analyzer = TagAnalyzer()
    speaker_talks = None

    def analyse(self, content):
        self.tag_analyzer.analyse(content)

        # 将内容拆分为对白片段
        self.speaker_talks = self.split_to_double_linked(content)

        # 合并同一行内的画外音
        self.combine_over_voice(self.speaker_talks)

        # 完善发言人
        self.complete_speaker(self.speaker_talks)

        for speak in self.speaker_talks.datas():
            logging.debug(speak)

    @staticmethod
    def split_to_double_linked(content):
        """
        将多行文本拆分成对白片段，装入双链表
        :param content: 多行文本
        :return: 双链表头结点
        """
        head = None
        node = None
        row_num = 0
        for line in content.split("\n"):
            row_num += 1
            line = line.strip()

            for piece in re_word_in_quote.split(line):
                if piece:
                    if not head:
                        head = DoubleLinkedNode(SpeakerTalk(row_num, piece))
                        node = head
                    else:
                        node = node.insert_after(SpeakerTalk(row_num, piece))

        return head

    @staticmethod
    def complete_speaker(node):
        """
        通过上下文内容完善指定结点的发言人
        """
        for n in node.nodes():
            if re_word_in_quote.match(n.data.talk):
                if n.prev and n.prev.data.row_num == n.data.row_num:
                    match = re.search("([^？。！]*)：$", n.prev.data.talk)
                    if match:
                        prev_says = match.group(1)
                        print("/".join(jieba.cut(prev_says)))

                # TODO: 分析说话者
                speaker = "Somebody"
            else:
                # 未被括号引用的内容，都是画外音
                speaker = "VoiceOver"

            n.data.speaker = speaker

        return node

    @staticmethod
    def combine_over_voice(node):
        """
        从指定节点开始合并同一行内的画外音
        :param node: 指定结点
        :return: 返回传入的结点
        """

        for n in node.nodes():
            if re_word_in_quote.match(n.data.talk):
                if n.prev and n.prev.data.row_num == n.data.row_num \
                        and not re_end_with_noword.match(n.prev.data.talk):
                    # 排除简单引用的情况，如：在整个科学院系统都素有“鬼才”之称，“鬼才”就不是对话内容
                    # 规则是与前文直接连续，无换行符或标点间隔
                    n.prev.data.talk += n.data.talk  # 合并内容
                    n.delete()

                    if n.next and n.next.data.row_num == n.data.row_num:
                        n.prev.data.talk += n.next.data.talk
                        n.next.delete()

        return node


if __name__ == '__main__':
    time_begin = time.perf_counter()

    tokenizer = SpeakerTalkAnalyzer()
    with open('res/材料帝国1.txt', 'r', encoding='UTF-8') as file:
        tokenizer.analyse(file.read())

    time_end = time.perf_counter()
    logging.info(f"time cost: {time_end - time_begin}")
