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
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("pydub").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

re_word_in_quote = re.compile("(“.*?”)")
re_word_in_quote_no_punctuation = re.compile("(“[\u4E00-\u9FD5a-zA-Z0-9]+”)")
re_end_with_punctuation = re.compile(".*[^\u4E00-\u9FD5a-zA-Z0-9]$")
re_begin_with_punctuation = re.compile("[^\u4E00-\u9FD5a-zA-Z0-9].*$")


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
    dialogues = None

    def analyse(self, sentence):
        self.names = {k: v for k, v in self.name_cutter.extract_names(sentence)}

        # 将内容拆分为对白片段
        self.dialogues = self.split_to_double_linked(sentence)

        # 合并同一行内的画外音
        self.combine_over_voice(self.dialogues)

        # 完善发言人
        self.complete_speaker(self.dialogues)

        line_count = 0
        speaker_count = 0
        for dialogue in self.dialogues.nodes():
            line_count += 1
            speaker_count += int(bool(dialogue.speaker))
        logger.info(f"analyse done, line_count: {line_count}, speaker_count: {speaker_count}, rate = "
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

    def get_dialogues(self):
        return self.dialogues.nodes() if self.dialogues else None

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
            speaker = self.__get_most_possible_speaker(self.__first_sentence(node.next.line))
            if speaker:
                return speaker

        # 查找同一行的前部分
        if node.prev and node.prev.row_num == node.row_num and not node.prev.is_in_quote:
            speaker = self.__get_most_possible_speaker(self.__last_sentence(node.prev.line))
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

    def __first_sentence(self, paragraph):
        _re_sentence_punctuation = re.compile("[！？。]", re.U)
        sentences = _re_sentence_punctuation.split(paragraph)
        return sentences[0]

    def __last_sentence(self, paragraph):
        _re_sentence_punctuation = re.compile("[！？。]", re.U)
        sentences = _re_sentence_punctuation.split(paragraph)
        return paragraph

    def __get_most_possible_speaker(self, sentence):
        tmp_speakers = []
        for frag in self.list_sub_words(sentence):
            # 找出句子中所有人名
            name_count = self.names.get(frag, 0)
            if name_count > 0:
                tmp_speakers.append((frag, name_count))

        speakers = []
        n = len(tmp_speakers)
        for i in range(n):
            if (i < n - 1 and len(tmp_speakers[i + 1][0]) > len(tmp_speakers[i][0])
                    and tmp_speakers[i + 1][0][:len(tmp_speakers[i][0])] == tmp_speakers[i][0]):
                continue
            else:
                speakers.append(tmp_speakers[i])

        if speakers:
            return speakers[0][0] + str(speakers[0][1])

        # if speakers:
        #     return "".join([a + str(b) for a, b in speakers])

        # 未查找到已有姓名的情况，返回第一个模式匹配到的姓名
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
                if (n.prev and n.prev.row_num == n.row_num and not re_end_with_punctuation.match(n.prev.line)) \
                        or (n.prev and n.prev.row_num != n.row_num
                            and n.next and n.next.row_num == n.row_num
                            and not re_begin_with_punctuation.match(n.next.line)
                            and re_word_in_quote_no_punctuation.match(n.line)):
                    # 排除简单引用的情况，
                    # 如：在整个科学院系统都素有“鬼才”之称。“鬼才”就不是对话内容。规则是与前文直接连续，无换行符或标点间隔
                    # 如：“明白人”当家。“明白人”就不是对话内容，规则是与后文直接连续，但引号内无标点
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

    def play(self):
        for dialogue in self.get_dialogues():
            if dialogue.speaker not in self.speaker_tones:
                if dialogue.speaker:
                    gender = ngender.guess(dialogue.speaker)[0]
                    tone = self.default_male_tone.clone() if gender == 'male' else self.default_female_tone.clone()
                    tone.alias = dialogue.speaker
                else:
                    tone = self.voiceover_tone.clone()
                    tone.alias = 'VoiceOver'
                self.speaker_tones[dialogue.speaker] = tone
            self.baidu_speech.append_speech(dialogue.line, self.speaker_tones[dialogue.speaker])
        self.baidu_speech.play(export_only=True)

    def print_dialogues(self):
        last_row_num = -1
        for dialogue in self.get_dialogues():
            row_num = '' if last_row_num == dialogue.row_num else dialogue.row_num
            last_row_num = dialogue.row_num
            print(f"{'{0:<5}'.format(row_num)} [{'{0:{1}<3}'.format(dialogue.speaker, chr(12288))}] {dialogue.line}")


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
    teller.add_word('日本人', 500, 'nr')
    teller.add_word('文化人', 500, 'nr')
    teller.set_voiceover_tone(BaiduSpeech.Tone('旁白', per=3))  # 情感合成-度逍
    teller.set_default_male_tone(BaiduSpeech.Tone(per=1))
    teller.set_default_female_tone(BaiduSpeech.Tone(per=0))
    teller.set_tone('秦海', BaiduSpeech.Tone('秦海', per=106, pit=6))  # 普通男声，音调加高，声音更年轻
    teller.analyse(jamen_utils.load_text(book))
    teller.print_dialogues()
    # teller.play()

    time_end = time.perf_counter()
    logger.info(f"time cost: {time_end - time_begin}")
