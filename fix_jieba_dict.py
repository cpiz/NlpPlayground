import logging
import sys

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(filename)s: %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _load_dict(dict_path, dict):
    logger.debug(f"load dict['{dict_path}']...")
    with open(dict_path, 'r', encoding='UTF-8') as f:
        for line in [l.strip() for l in f if l.strip()]:
            if line[:1] == '#':
                # 忽略注释
                continue

            word, weight, prop = (line + '  ').split(' ')[:3]
            weight = int(weight) if weight else 1
            if word not in dict:
                dict[word] = weight, prop
    logger.debug(f"load dict['{dict_path}'] done, size: {len(dict)} ")


if __name__ == '__main__':
    chn_dict = {}
    jieba_dict = {}

    _load_dict('dict\\jieba.dict', jieba_dict)
    logger.debug(f"jieba dict count: {len(jieba_dict)}")

    _load_dict('dict\\chinese.dict', chn_dict)
    _load_dict('dict\\chinese_regions.dict', chn_dict)
    _load_dict('dict\\world_countries.dict', chn_dict)
    _load_dict('dict\\chinese_colleges.dict', chn_dict)
    _load_dict('dict\\chinese_stop_words.dict', chn_dict)
    logger.debug(f"chn dict count: {len(chn_dict)}")

    count = 0
    for k, v in [(k, v) for k, v in jieba_dict.items()]:
        if v[1] in ('nr', 'nrt'):
            if len(k) == 1 or k in chn_dict:
                jieba_dict[k] = v[0], 'n'
            else:
                del jieba_dict[k]
                # print(k)
                count += 1

    with open('dict\\jieba_without_nr.dict', 'w', encoding='UTF-8') as file:
        lines = [f"{k} {v[0]} {v[1]}\n" for k, v in jieba_dict.items()]
        file.writelines(lines)
    print(lines)
