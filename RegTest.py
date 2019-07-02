# encoding=utf-8
import re

if __name__ == '__main__':
    str = "从算法原理上来看，，基础都是词频统计，,,,只是TD-IDF通过IDF来调整词频的权值 而Text,Rank通过上下文的连接数来调整词频的权值。"

    # re_han1 = re.compile("[^\u4E00-\u9FD5a-zA-Z0-9_\\-]+", re.U)
    # re_han2 = re.compile("([^\u4E00-\u9FD5a-zA-Z0-9_\\-]+)", re.U)
    # re_han3 = re.compile("[^\u4E00-\u9FD5]+", re.U)
    # re_han4 = re.compile("([^\u4E00-\u9FD5]+)", re.U)
    # re_han5 = re.compile("[\u4E00-\u9FD5]+", re.U)
    # re_han6 = re.compile("([\u4E00-\u9FD5]+)", re.U)
    # re_han7 = re.compile("([\u4E00-\u9FD5a-zA-Z0-9+#&\\._%\\-]+)", re.U)
    # re_han8 = re.compile("[a-zA-Z0-9_\\-]+", re.U)
    # re_han9 = re.compile("([a-zA-Z0-9_\\-，]+)", re.U)
    re_han0 = re.compile("([\u4E00-\u9FD5]+|[a-zA-Z0-9_\\-]+)", re.U)  # 这个好

    # print(re_han1.split(str))
    # print(re_han2.split(str))
    # print(re_han3.split(str))
    # print(re_han4.split(str))
    # print(re_han5.split(str))
    # print(re_han6.split(str))
    # print(re_han7.split(str))
    # print(re_han8.split(str))
    # print(re_han9.split(str))
    print(re_han0.split(str))

    re_asc = re.compile("[a-zA-Z0-9_\\-]+", re.U)

    for b in re_han0.split(str):
        if re_asc.match(b):
            print(b)
