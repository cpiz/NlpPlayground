# encoding=utf-8
import logging
import re
import sys
import time

import ngender

import jamen_utils
from baidu_speech import BaiduSpeech
from double_linked_node import DoubleLinkedListNode
from jamen_cutter import JamenCutter

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(filename)s: %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logging.getLogger("connectionpool").setLevel(logging.NOTSET)

re_word_in_quote = re.compile("(“.*?”)")
re_end_with_noword = re.compile(".*[^\u4E00-\u9FD5a-zA-Z0-9]$")


# re_quote = re.compile("[“”]")
# “王晓晨，原来是你住在对面啊。”宁默倒也认识那姑娘，他用手指了指秦海，说道：“这是秦海，我哥们。他是农机技校毕业的，分到咱们厂里工作，以后就和你住对门了。”

class SpeakerTalk(DoubleLinkedListNode):
    speaker = ""
    """角色名称"""

    line = ""
    """说话内容"""

    row_num = 0
    """说话内容所在的行号，从第1行开始"""

    is_in_quote = False

    def __init__(self, row_num, line):
        DoubleLinkedListNode.__init__(self, None, None)
        self.row_num = row_num
        self.speaker = ""
        self.line = line
        self.is_in_quote = re_word_in_quote.match(line) is not None
        # logging.debug((speaker, talk))

    def __str__(self):
        speaker = self.speaker if self.speaker else ''
        return f"[{'{0:>4}'.format(self.row_num)}][{'{0:{1}>3}'.format(speaker, chr(12288))}] {self.line}"

    def find_prev_line(self):
        """
        查找上一句台词（非旁白）
        :return:
        """
        prev = self.prev
        while prev and not prev.is_in_quote:
            prev = prev.prev
        return prev


class StoryTeller:
    MIN_HAN_WORD_LENGTH = 2
    MAX_HAN_WORD_LENGTH = 6

    baidu_speech = BaiduSpeech()
    name_cutter = JamenCutter()

    names = {}
    speaker_tones = {}
    default_male_tone = BaiduSpeech.Tone(pit=1)
    default_female_tone = BaiduSpeech.Tone(pit=0)
    voiceover_tone = BaiduSpeech.Tone(pit=3)
    speaker_talks = None

    def analyse(self, sentence):
        self.names = {k: v for k, v in self.name_cutter.extract_names(sentence)}

        # 将内容拆分为对白片段
        self.speaker_talks = self.split_to_double_linked(sentence)

        # 合并同一行内的画外音
        self.combine_over_voice(self.speaker_talks)

        # 完善发言人
        self.complete_speaker(self.speaker_talks)

        line_count = 0
        speaker_count = 0
        for speak in self.speaker_talks.nodes():
            line_count += 1
            speaker_count += int(bool(speak.speaker))
        logging.info(f"analyse done, line_count: {line_count}, speaker_count: {speaker_count}, rate = "
                     f"{speaker_count / line_count}")

    def add_word(self, word, weight=1, prop='x'):
        self.name_cutter.add_word(word, weight, prop)

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
                        head = SpeakerTalk(row_num, piece)
                        node = head
                    else:
                        node = node.insert_after(SpeakerTalk(row_num, piece))

        return head

    def get_speaker_talks(self):
        return self.speaker_talks.nodes() if self.speaker_talks else None

    def complete_speaker(self, node):
        """
        通过上下文内容完善指定结点的发言人
        """
        for n in node.nodes():
            if n.is_in_quote:
                # 未被括号引用的内容，即对话
                speaker = self._get_most_possible_speaker(n)
            else:
                # 未被括号引用的内容，都是画外音
                speaker = ""

            n.speaker = speaker

        return node

    def _get_most_possible_speaker(self, node):
        # 查找同一行的后部分
        if node.next and node.next.row_num == node.row_num and not node.next.is_in_quote:
            speaker = self.__get_most_possible_speaker(node.next.line)
            if speaker:
                return speaker

        # 查找同一行的前部分
        if node.prev and node.prev.row_num == node.row_num and not node.prev.is_in_quote:
            speaker = self.__get_most_possible_speaker(node.prev.line)
            if speaker:
                return speaker

        # 查找上一行，看是否以冒号结尾
        prev = node.prev
        if prev and not prev.is_in_quote and prev.line[-1:] == '：':
            speaker = self.__get_most_possible_speaker(prev.line)
            if speaker:
                return speaker

        # 查找上上句对话
        prev = node.find_prev_line()
        if prev:
            prev = prev.find_prev_line()
            if prev:
                return prev.speaker

        next = node.next
        while next and next.is_in_quote:
            next = next.next  # 查找下一行
        speaker = self.__get_most_possible_speaker(next.line) if next else ''
        if speaker:
            return speaker

        return None

    def __get_most_possible_speaker(self, sentence):
        # 先尝试找高频文字
        for frag in self.list_sub_words(sentence):
            name_count = self.names.get(frag, 0)
            if name_count > 0:
                return frag  # 返回第一个名字

        for frag in self.list_sub_words(sentence):
            if self.name_cutter.match_chinese_name(frag) > 0:
                return frag

        return ''

    def list_sub_words(self, clip):
        """
        从一个断句中列举出所有词的组合
        :param clip:
        :return:
        """
        n = len(clip)
        for begin in range(0, n - self.MIN_HAN_WORD_LENGTH + 1):
            for end in range(begin + self.MIN_HAN_WORD_LENGTH,
                             begin + min(n - begin, self.MAX_HAN_WORD_LENGTH) + 1):
                yield clip[begin:end]

    @staticmethod
    def combine_over_voice(node):
        """
        从指定节点开始合并同一行内的画外音
        :param node: 指定结点
        :return: 返回传入的结点
        """
        for n in node.nodes():
            if n.is_in_quote:
                if n.prev and n.prev.row_num == n.row_num \
                        and not re_end_with_noword.match(n.prev.line):
                    # 排除简单引用的情况，如：在整个科学院系统都素有“鬼才”之称，“鬼才”就不是对话内容
                    # 规则是与前文直接连续，无换行符或标点间隔
                    n.prev.line += n.line  # 合并内容
                    n.delete()

                    if n.next and n.next.row_num == n.row_num:
                        n.prev.line += n.next.line
                        n.next.delete()

        return node

    def set_tone(self, speaker_name, tone):
        self.speaker_tones[speaker_name] = tone

    def set_default_male_tone(self, tone):
        self.default_male_tone = tone

    def set_default_female_tone(self, tone):
        self.default_female_tone = tone

    def set_voiceover_tone(self, tone):
        self.voiceover_tone = tone

    def play(self, book_path):
        content = jamen_utils.load_text(book_path)
        self.analyse(content)

        last_row_num = -1
        for speak in self.get_speaker_talks():
            row_num = '' if last_row_num == speak.row_num else speak.row_num
            last_row_num = speak.row_num

            if speak.speaker:
                print(f"{'{0:<5}'.format(row_num)} [{'{0:{1}<3}'.format(speak.speaker, chr(12288))}] {speak.line}")
                pass
            else:
                print(f"{'{0:<5}'.format(row_num)} [{'{0:{1}<3}'.format('', chr(12288))}] {speak.line}")

        for speak_talk in self.get_speaker_talks():
            if speak_talk.speaker not in self.speaker_tones:
                if speak_talk.speaker:
                    gender = ngender.guess(speak_talk.speaker)[0]
                    tone = self.default_male_tone.clone() if gender == 'male' else self.default_female_tone.clone()
                    tone.alias = speak_talk.speaker
                else:
                    tone = self.voiceover_tone.clone()
                    tone.alias = 'VoiceOver'
                self.speaker_tones[speak_talk.speaker] = tone
            self.baidu_speech.append_speech(speak_talk.line, self.speaker_tones[speak_talk.speaker])
        self.baidu_speech.play()


if __name__ == '__main__':
    time_begin = time.perf_counter()

    book = 'res/材料帝国1.txt'
    # book = 'res/材料帝国.txt'
    # book = 'D:\\OneDrive\\Books\\临高启明.txt'
    # book = 'E:\\BaiduCloud\\Books\\庆余年.txt'
    # book = 'E:\\BaiduCloud\\Books\\侯卫东官场笔记.txt'
    # book = 'D:\\OneDrive\\Books\\重生之官路商途原稿加最好的蛇足续版.txt'
    # book = 'E:\\BaiduCloud\\Books\\兽血沸腾.txt'
    # book = 'E:\\BaiduCloud\\Books\\将夜.txt'
    # book = 'E:\\BaiduCloud\\Books\\流氓高手II.txt'
    # book = 'E:\\BaiduCloud\\Books\\紫川.txt'
    # book = 'E:\\BaiduCloud\\Books\\活色生香.txt'
    # book = 'E:\\BaiduCloud\\Books\\弹痕.txt'
    teller = StoryTeller()
    teller.add_word('日本人', 1000, 'nr')
    teller.set_voiceover_tone(BaiduSpeech.Tone('旁白', per=3))  # 情感合成-度逍
    teller.set_default_male_tone(BaiduSpeech.Tone(per=1))
    teller.set_default_female_tone(BaiduSpeech.Tone(per=0))
    # teller.set_tone('秦海', BaiduSpeech.Tone('秦海', per=1, pit=6))  # 普通男声，音调加高，声音更年轻
    # teller.set_tone('王晓晨', BaiduSpeech.Tone('王晓晨', per=0, pit=5))
    teller.play(book)

    time_end = time.perf_counter()
    logging.info(f"time cost: {time_end - time_begin}")
