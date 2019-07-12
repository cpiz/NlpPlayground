# encoding=utf-8
import logging
import re
import sys
import time

from DoubleLinkedNode import DoubleLinkedNode
from tag_analyzer_2 import TagAnalyzer

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

    in_quote = False

    def __init__(self, row_num, talk):
        self.row_num = row_num
        self.speaker = ""
        self.talk = talk
        self.in_quote = re_word_in_quote.match(talk) is not None
        # logging.debug((speaker, talk))

    def __str__(self):
        speaker = self.speaker if self.speaker else None
        return f"row[{self.row_num}]{speaker}: {self.talk}"


class SpeakerTalkAnalyzer:
    tag_analyzer = TagAnalyzer()
    speaker_talks = None

    def analyse(self, sentence):
        self.tag_analyzer.analyse(sentence)

        # 将内容拆分为对白片段
        self.speaker_talks = self.split_to_double_linked(sentence)

        # 合并同一行内的画外音
        self.combine_over_voice(self.speaker_talks)

        # 完善发言人
        self.complete_speaker(self.speaker_talks)

        for speak in self.speaker_talks.datas():
            logging.debug(speak)

    @staticmethod
    def split_to_double_linked(sentence):
        """
        将多行文本拆分成对白片段，装入双链表
        :param sentence: 多行文本
        :return: 双链表头结点
        """
        head = None
        node = None
        row_num = 0
        for line in sentence.split("\n"):
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

    def complete_speaker(self, node):
        """
        通过上下文内容完善指定结点的发言人
        """
        for n in node.nodes():
            if n.data.in_quote:
                # 未被括号引用的内容，即对话

                # 分析说话者

                # 查找当前对话同一行的后部分

                # if n.next and n.next.data.row_num == n.data.row_num:
                #     print([word + 1 for word in word, self.tag_analyzer.list_sub_words(n.next.data.talk)])

                # print(list(map(self.tag_analyzer.get_tag, self.tag_analyzer.list_sub_words(n.next.data.talk))))

                # print(
                #     [word, self.tag_analyzer.get_tag(word) for word in ])

                # if n.prev and n.prev.data.row_num == n.data.row_num:
                #     match = re.search("([^？。！]*)：$", n.prev.data.talk)
                #     if match:
                #         prev_says = match.group(1)
                #         print("/".join(jieba.cut(prev_says)))

                # TODO: 分析说话者
                speaker = self.__get_most_possible_speaker(self.__get_most_possible_speaker_sentence(n))
            else:
                # 未被括号引用的内容，都是画外音
                speaker = "VoiceOver"

            n.data.speaker = speaker

        return node

    def __get_most_possible_speaker(self, sentence):
        frags = {}
        for frag in self.tag_analyzer.list_sub_words(sentence):
            frag_count = self.tag_analyzer.get_tag_count(frag)
            if frag_count > 0:
                frags[frag] = frag_count
        # for frag, count in sorted(frags.items(), key=lambda x: x[1], reverse=True):

        if len(frags) == 0:
            return ''

        speaker = sorted(frags.items(), key=lambda x: x[1], reverse=True)[0][0]
        return speaker

    @staticmethod
    def __get_most_possible_speaker_sentence(n):
        if n.next and n.next.data.row_num == n.data.row_num and not n.next.data.in_quote:
            return n.next.data.talk  # 查找当前对话同一行的后部分
        elif n.prev and n.prev.data.row_num == n.data.row_num and not n.prev.data.in_quote:
            return n.prev.data.talk  # 查找当前对话同一行的前部分
        else:
            next = n.next
            while next and next.data.in_quote:
                next = next.next
            return next.data.talk if next else None

    @staticmethod
    def combine_over_voice(node):
        """
        从指定节点开始合并同一行内的画外音
        :param node: 指定结点
        :return: 返回传入的结点
        """

        for n in node.nodes():
            if n.data.in_quote:
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

    analyzer = SpeakerTalkAnalyzer()

    book_path = 'res/材料帝国1.txt'
    # book_path = 'res/test_book.txt'
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
    # book_path = 'E:\\BaiduCloud\\Books\\弹痕.txt'
    try:
        with open(book_path, 'r', encoding='UTF-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        with open(book_path, 'r', encoding='gb18030', errors='ignore') as file:
            content = file.read()
    analyzer.analyse(content)

    time_end = time.perf_counter()
    logging.info(f"time cost: {time_end - time_begin}")
