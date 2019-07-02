# encoding=utf-8
import jieba.analyse

# jieba词性对照表
# https://gist.github.com/hscspring/c985355e0814f01437eaf8fd55fd7998

if __name__ == '__main__':
    with open('res/材料帝国1.txt', 'r', encoding='UTF-8') as file:
        content = file.read().replace("\n", "")

    # cut_all=True【全模式】: 我/ 来到/ 北京/ 清华/ 清华大学/ 华大/ 大学
    # cut_all=False【精确模式】: 我/ 来到/ 北京/ 清华大学
    seg_list = jieba.cut(content, cut_all=False, HMM=True)
    print("/".join(seg_list))
