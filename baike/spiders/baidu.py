from pathlib import Path

import scrapy
from ..items import BaikeItem
import json
import re
import requests


class BaiduSpider(scrapy.Spider):
    name = 'baidu'
    allowed_domains = ['baike.baidu.com']
    person = input("请输入名字：")
    start_urls = ['https://baike.baidu.com/item/' + person, ]

    def string_handling(self, str_list):
        new_str = ''
        clean_text = [t.strip() for t in str_list if t.strip()]  # 去除文本中的特殊字符
        for text in clean_text:  # 除去[2]这个鬼东西
            if text[0] != '[':
                new_str += text
        new_str = new_str.replace('\xa0', '')
        return new_str

    def download_html(self, response):
        page = response.url.split("/")[-2]
        filename = f'baidu-{page}.html'
        Path(filename).write_bytes(response.body)

    def get_summary(self, response):
        text = response.xpath(
            '//div[@class="lemma-summary J-summary"]//text()').extract()
        return self.string_handling(text)

    def get_basic_info(self, response):
        basic_info = {}
        pos = response.xpath('//div[@class="basic-info J-basic-info cmn-clearfix"]')[0]  # 定位到基本休息栏
        list_1 = pos.xpath("child::dl").xpath("child::dt")  # 标题
        list_2 = pos.xpath("child::dl").xpath("child::dd")  # 内容
        for i in range(len(list_1)):
            left = list_1[i].xpath(".//text()").extract()
            right = list_2[i].xpath(".//text()").extract()
            basic_info[self.string_handling(left)] = self.string_handling(right)
        return basic_info

    def get_relation(self, response):
        url = response.xpath('//link[@hreflang="x-default"]').xpath('@href').extract()[0]
        person_id = re.findall(r'\/+\d+', url[-14:])
        person_id = (person_id[-1])[1:]
        name = response.url.split("/")[-2]
        url = 'https://baike.baidu.com/starmap/api/gethumanrelationcard?lemmaId=' + person_id + '&lemmaTitle=' + name
        res = requests.get(url, verify=False)
        relation = res.json()["list"]
        return relation

    def get_life(self, response):
        life = []
        flag = 0
        pos = response.xpath('//div[@class="anchor-list "]')[0]  # 定位到人物生平位置
        title = pos.xpath("child::a").xpath("@name").extract()[2]
        if title == '人物生平' or title == '生平经历' or title == '人物经历' or title == '人物履历' or title == '早年经历':
            while flag < 2:
                if pos.xpath("child::*[1]"):
                    if pos.xpath("child::*[1]")[0].xpath("name()").get() == "h2":
                        flag += 1
                info = self.string_handling(pos.xpath('.//text()').extract())
                if info:
                    info = info.replace('编辑播报', '')
                    life.append(info)
                pos = pos.xpath("following-sibling::*[1]")[0]
        return life[1:-1]

    def save_json(self, person, summary, basic_info, relation, life):
        with open('./result/' + str(self.person) + '.json', 'w', encoding='utf-8') as fw:
            json.dump({"人物名称": self.person, "人物简介": summary, "基本信息": basic_info, "人物关系": relation, "人物生平": life[1:-1]},
                      fw, ensure_ascii=False, indent=4)

    def parse(self, response):
        # self.download_html(response)
        items = BaikeItem()
        items['name'] = self.person

        # 简介
        summary = self.get_summary(response)
        items['summary'] = summary
        # 基本信息
        basic_info = self.get_basic_info(response)
        items['basic_info'] = basic_info
        # 人物关系
        relation = self.get_relation(response)
        items['relation'] = relation
        # 生平
        life = self.get_life(response)
        items['biography'] = life

        self.save_json(self.person, summary, basic_info, relation, life)

        yield items
