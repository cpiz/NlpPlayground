import logging
import re
import sys
import threading
from time import sleep, time
from urllib.parse import quote

import playsound
import requests

import jamen_utils

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(filename)s: %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

APP_ID = 16634868

# 填写网页上申请的appkey 如 API_KEY="g8eBUMSokVB1BHGmgxxxxxx"
API_KEY = 'OTTnHiPsNxpQ9Id68qfhhVwO'

# 填写网页上申请的APP SECRET 如 SECRET_KEY="94dc99566550d87f8fa8ece112xxxxx"
SECRET_KEY = '94Y6bfKczlU00ZyNkE3ESdkzkD1rxtPV'

re_end_with_exclamation = re.compile('“.*[！!]”')
re_word_in_quote = re.compile("(“.*?”)")


class BaiduSpeech:
    __app_id = 0
    __api_key = ''
    __secret_key = ''
    __access_token = ""
    __session = None

    __request_list = []
    __play_list = []

    class Tone:
        alias = None
        """发音人别名"""
        per = 0
        """发音人选择, 0为普通女声，1为普通男生，3为情感合成-度逍遥，4为情感合成-度丫丫，默认为普通女声"""
        vol = 5
        """音量，取值0-15，默认为5中音量"""
        pit = 5
        """音调，取值0-15，默认为5中语调"""
        spd = 5
        """语速，取值0-15，默认为5中语速"""

        def __init__(self, alias="Unknown", per=0, vol=5, pit=5, spd=5):
            self.alias = alias
            self.per = per
            self.vol = vol
            self.pit = pit
            self.spd = spd

        def clone(self):
            ret = BaiduSpeech.Tone(self.alias)
            ret.per = self.per
            ret.vol = self.vol
            ret.pit = self.pit
            ret.spd = self.spd
            return ret

    def __init__(self, app_id=APP_ID, api_key=API_KEY, secret_key=SECRET_KEY):
        self.__app_id = app_id
        self.__api_key = api_key
        self.secret_key = secret_key
        jamen_utils.makesure_dir('mp3')

    def append_speech(self, text, tone=Tone()):
        self.__request_list.append((text, tone))

    def play(self):
        t1 = threading.Thread(target=self.__run_text2audio)
        t1.setDaemon(True)
        t1.start()

        t2 = threading.Thread(target=self.__run_playsound)
        t2.setDaemon(True)
        t2.start()

        t2.join()

    def __get_http_session(self):
        if not self.__session:
            self.__session = requests.Session()
        return self.__session

    def __request_speech(self, text, tone=Tone()):
        if not self.__access_token:
            self.__request_auth()

        spd_adjust = 0
        vol_adjust = 0
        pit_adjust = 0

        if re_word_in_quote.match(text):
            # 对白句，提速
            spd_adjust += 1

            if re_end_with_exclamation.match(text):
                # 感叹句，增加音量
                vol_adjust += 5

        r = self.__get_http_session().post("https://tsn.baidu.com/text2audio",
                                           data={
                                               'tex': quote(text),
                                               'tok': self.__access_token,
                                               'cuid': 'jamen',
                                               'ctp': '1',
                                               'lan': 'zh',
                                               'spd': tone.spd + spd_adjust,
                                               'pit': tone.pit + pit_adjust,
                                               'vol': tone.vol + vol_adjust,
                                               'per': tone.per,
                                               'aue': '3'
                                               # tex	必填	合成的文本，使用UTF-8编码。小于2048个中文字或者英文数字。（文本在百度服务器内转换为GBK后，长度必须小于4096字节）
                                               # tok	必填	开放平台获取到的开发者access_token（见上面的“鉴权认证机制”段落）
                                               # cuid必填	用户唯一标识，用来计算UV值。建议填写能区分用户的机器 MAC 地址或 IMEI 码，长度为60字符以内
                                               # ctp	必填	客户端类型选择，web端填写固定值1
                                               # lan	必填	固定值zh。语言选择,目前只有中英文混合模式，填写固定值zh
                                               # spd	选填	语速，取值0-15，默认为5中语速
                                               # pit	选填	音调，取值0-15，默认为5中语调
                                               # vol	选填	音量，取值0-15，默认为5中音量
                                               # per	选填	发音人选择, 0为普通女声，1为普通男生，3为情感合成-度逍遥，4为情感合成-度丫丫，默认为普通女声
                                               # aue	选填	3为mp3格式(默认)； 4为pcm-16k；5为pcm-8k；6为wav（内容同pcm-16k）; 注意aue=4或者6是语音识别要求的格式，但是音频内容不是语音识别要求的自然人发音，所以识别效果会受影响。
                                           }
                                           )
        """
        如果合成成功，返回的Content-Type以“audio”开头
        aue =3 ，返回为二进制mp3文件，具体header信息 Content-Type: audio/mp3；
        aue =4 ，返回为二进制pcm文件，具体header信息 Content-Type:audio/basic;codec=pcm;rate=16000;channel=1
        aue =5 ，返回为二进制pcm文件，具体header信息 Content-Type:audio/basic;codec=pcm;rate=8000;channel=1
        aue =6 ，返回为二进制wav文件，具体header信息 Content-Type: audio/wav；
        如果合成出现错误，则会返回json文本，具体header信息为：Content-Type: application/json。其中sn字段主要用于DEBUG追查问题，如果出现问题，可以提供sn帮助确认问题。
        错误示例
        {"err_no":500,"err_msg":"notsupport.","sn":"abcdefgh","idx":1}
        """
        content_type = r.headers["Content-Type"]
        if content_type == "application/json":
            json_result = r.json()
            logger.error(f"request text2audio error, err_no: {json_result['err_no']}, "
                         f"err_msg: {json_result['err_msg']}")
        elif content_type == "audio/mp3":
            audio_file_path = f"mp3/{self.__current_milli_time()}.mp3"
            with open(audio_file_path, 'wb') as file:
                file.write(r.content)
            return audio_file_path
        else:
            logger.error(f"request text2audio error, unexpected content-type")
            return ""

    def __request_auth(self):
        """
        鉴权
        :return:
        """
        r = self.__get_http_session().get(
            f'https://openapi.baidu.com/oauth/2.0/token',
            params={
                'grant_type': 'client_credentials',
                'client_id': self.__api_key,
                'client_secret': self.secret_key,
            })
        json_result = r.json()
        self.__access_token = json_result["access_token"]

    @staticmethod
    def __current_milli_time():
        return int(round(time() * 1000))

    def __run_playsound(self):
        while True:
            idle = True
            if self.__play_list:
                text, tone, audio = self.__play_list.pop(0)
                logger.debug(f"play {audio}[{tone.alias}]{text}")
                self.__play_audio(audio)
                # if os.path.exists(audio):
                #     os.remove(audio)
                idle = False

            if idle:
                sleep(0.020)

    def __run_text2audio(self):
        while True:
            idle = True
            while len(self.__play_list) < 3 and self.__request_list:
                text, tone = self.__request_list.pop(0)
                audio = self.__request_speech(text, tone)
                if audio:
                    self.__play_list.append((text, tone, audio))
                idle = False

            if idle:
                sleep(0.020)

    @staticmethod
    def __play_audio(path):
        try:
            playsound.playsound(path, True)
        except UnicodeDecodeError as err:
            logger.warning(f'play error, error: {err}"')


if __name__ == '__main__':
    baidu_speech = BaiduSpeech()
    baidu_speech.append_speech("一二三四五，上山打老虎，老虎没打着，打着小松鼠")
    baidu_speech.append_speech("一二三四五，上山打老虎，老虎没打着，打着小松鼠")
    baidu_speech.append_speech("一二三四五，上山打老虎，老虎没打着，打着小松鼠")
    baidu_speech.append_speech("一二三四五，上山打老虎，老虎没打着，打着小松鼠")
    baidu_speech.append_speech("一二三四五，上山打老虎，老虎没打着，打着小松鼠")
    baidu_speech.play()
