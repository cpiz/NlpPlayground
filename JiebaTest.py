# encoding=utf-8
import jieba
import jieba.analyse

# jieba词性对照表
# https://gist.github.com/hscspring/c985355e0814f01437eaf8fd55fd7998

if __name__ == '__main__':
    with open('res/材料帝国.txt', 'r', encoding='UTF-8') as file:
        content = file.read().replace("\n", "")

    # seg_list = jieba.cut(content, cut_all=False)
    # print("/".join(seg_list))

    # tags = jieba.analyse.extract_tags(content, topK=100000, withWeight=True, withFlag=True)
    # tags = jieba.analyse.extract_tags(content, topK=200, withWeight=True, withFlag=True, allowPOS=['nr'])
    # tags = jieba.analyse.extract_tags(content, topK=200, withWeight=True, withFlag=True,
    #                                   allowPOS=['ns', 'n', 'vn', 'v', 'nr'])
    # for tag in tags:
    #     print(f"{tag}")

    # tags2 = jieba.analyse.textrank(content, topK=20, withWeight=True, withFlag=True,allowPOS=['nr'])
    # for tag in tags:
    #     print(f"{tag}")
