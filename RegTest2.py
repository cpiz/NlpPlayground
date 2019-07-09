# encoding=utf-8
import re

if __name__ == '__main__':
    str1 = "“王晓晨，原来是你住在对面啊。”宁默倒也认识那姑娘，他用手指了指秦海，说道：“这是秦海，我哥们。他是农机技校毕业的，分到咱们厂里工作，以后就和你住对门了。”"
    str2 = "“王晓晨””，“原来是你住在对面啊。"

    # re_talk = re.compile("((^|[^\u4E00-\u9FD5a-zA-Z0-9])“(.*?)”([^“”]*?))", re.U)

    re_talk1 = re.compile("(^|[^\u4E00-\u9FD5a-zA-Z0-9])“(.*?)”([^“”]*)", re.U)
    re_talk2 = re.compile("([^“”]+(^|[^\u4E00-\u9FD5a-zA-Z0-9]))“(.*?)”", re.U)

    re_talk0 = re.compile("^\\s*“(.*?)”\\s*$", re.U)  # 整句话
    re_talk1 = re.compile("(^|[^\u4E00-\u9FD5a-zA-Z0-9])“(.*?)”([^“”]+)", re.U)  # 话在前，人在后
    re_talk2 = re.compile("([^“”]+(^|[^\u4E00-\u9FD5a-zA-Z0-9]))“(.*?)”", re.U)  # 人在前，话在后

    re_end_with_noword = re.compile(".*([^\u4E00-\u9FD5a-zA-Z0-9])")

    re_talk = re.compile("(“.*?”)")

    # print(re_talk0.search(str).groups())
    # print(re_talk1.search(str).groups())
    # print(re_talk2.search(str).groups())
    # print(re_talk.split(str1))
    # print(re_talk.split(str2))
    # print(re_end_with_noword.match("在整个科学院系统都素有-").groups())


    str = ',秦海,,宁中,,中英,,宁中英,,宁默,,韦宝,,宝林,韦宝林,萧东,东平,萧东平,刀片'
    print(str)
    print(re.findall(",([^,]*宁中[^,]*),", str, re.U))
