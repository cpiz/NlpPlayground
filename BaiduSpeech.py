from urllib.parse import quote

import playsound
import requests

APP_ID = 16634868

# 填写网页上申请的appkey 如 API_KEY="g8eBUMSokVB1BHGmgxxxxxx"
API_KEY = 'OTTnHiPsNxpQ9Id68qfhhVwO'

# 填写网页上申请的APP SECRET 如 SECRET_KEY="94dc99566550d87f8fa8ece112xxxxx"
SECRET_KEY = '94Y6bfKczlU00ZyNkE3ESdkzkD1rxtPV'

TEXT = "一二三四五，上山打老虎，老虎没打着，打着小松鼠"

if __name__ == '__main__':
    # 鉴权
    r = requests.get(
        f'https://openapi.baidu.com/oauth/2.0/token',
        params={
            'grant_type': 'client_credentials',
            'client_id': API_KEY,
            'client_secret': SECRET_KEY,
        })
    auth_result = r.json()
    access_token = auth_result["access_token"]
    print(f"access_token: '{access_token}'")

    # 语音合成
    r = requests.post("https://tsn.baidu.com/text2audio",
                      data={
                          'tex': quote(TEXT),
                          'tok': access_token,
                          'cuid': 'jamen',
                          'ctp': '1',
                          'lan': 'zh',
                          'spd': '5',
                          'pit': '5',
                          'vol': '5',
                          'per': '0',
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

    audio_file_name = "audio.mp3"
    with open(audio_file_name, 'wb') as file:
        file.write(r.content)
    playsound.playsound(audio_file_name, True)
