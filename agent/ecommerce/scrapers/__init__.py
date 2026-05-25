from .jd import JdScraper
from .pdd import PddScraper
from .taobao import TaobaoScraper

SCRAPER_CLASSES = {
    "jd": JdScraper,
    "jingdong": JdScraper,
    "京东": JdScraper,
    "taobao": TaobaoScraper,
    "淘宝": TaobaoScraper,
    "pdd": PddScraper,
    "pinduoduo": PddScraper,
    "拼多多": PddScraper,
}

