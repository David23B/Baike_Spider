from pathlib import Path

import scrapy
from ..items import BaikeItem
import json
import re
import requests
import urllib
import csv
from collections import defaultdict


class BaiduSpider(scrapy.Spider):
    name = 'baidu'
    person = input("请输入名字：")
    counts = int(input("请输入需要爬取的人数："))
    names_to_ids = {}
    ids = []
    pointer = 0
    allowed_domains = ['baike.baidu.com']
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
        filename = f'./results/baidu-{page}.html'
        Path(filename).write_bytes(response.body)

    def download_json(self, response):
        page = response.url.split("/")[-2]
        filename = f'./results/baidu-{page}.json'
        Path(filename).write_bytes(response.body)

    def get_summary(self, response):
        try:
            text = response.xpath(
                '//div[@class="lemma-summary J-summary"]//text()').extract()
            return self.string_handling(text)
        except:
            return 'ERROR:检索人物简介信息出错！'

    def get_basic_info(self, response):
        try:
            basic_info = {}
            pos = response.xpath('//div[@class="basic-info J-basic-info cmn-clearfix"]')[0]  # 定位到基本休息栏
            list_1 = pos.xpath("child::dl").xpath("child::dt")  # 标题
            list_2 = pos.xpath("child::dl").xpath("child::dd")  # 内容
            for i in range(len(list_1)):
                left = list_1[i].xpath(".//text()").extract()
                right = list_2[i].xpath(".//text()").extract()
                basic_info[self.string_handling(left)] = self.string_handling(right)
            return basic_info
        except:
            return 'ERROR:检索人物基本信息出错！'

    def get_relation(self, response):
        final_relation = defaultdict(list)
        try:
            url = response.xpath('//link[@hreflang="x-default"]').xpath('@href').extract()[0]
            id = re.findall(r'\/+\d+', url[-14:])
            id = (id[-1])[1:]
            if response.url.split("/")[-2] == 'item':
                name = response.url.split("/")[-1]
            else:
                name = response.url.split("/")[-2]
            if id not in self.ids:
                self.ids.append(id)
                self.names_to_ids[id] = urllib.parse.unquote(name)
            rela_url = 'https://baike.baidu.com/starmap/api/gethumanrelationcard?lemmaId=' + id + '&lemmaTitle=' + name
            relation = requests.get(rela_url).json()['list']
            if relation:
                for rel in relation:
                    final_relation[rel['relationName']].append(rel['lemmaTitle'])
                    if str(rel['lemmaId']) not in self.ids:
                        self.names_to_ids[str(rel['lemmaId'])] = urllib.parse.unquote(rel['lemmaTitle'])
                        self.ids.append(str(rel['lemmaId']))
                return final_relation
            else:
                final_relation["人物关系"].append("NONE")
                return final_relation
        except:
            return "[ERROR]检索人物关系信息出错"

    def get_life(self, response):
        try:
            life = []
            flag = 0
            pos = response.xpath('//div[@class="anchor-list  MARK_MODULE"]')[0]  # 定位到人物生平位置
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
            else:
                life.append("该人物没有人物生平相关信息")
                return life
        except:
            return "[ERROR]检索人物生平信息出错"

    def save_json(self, name, summary, basic_info, relation, life):
        name = urllib.parse.unquote(name)
        with open('./results/' + name + '.json', 'w', encoding='utf-8') as fw:
            json.dump({"人物名称": name, "人物简介": summary, "基本信息": basic_info, "人物关系": relation, "人物生平": life[1:-1]},
                      fw, ensure_ascii=False, indent=4)

    def save_csv(self, name, summary, basic_info, relation, life):
        csv_file = open('./KUN.csv', 'a', encoding='utf-8')
        writer = csv.writer(csv_file)
        writer.writerow([name, summary, basic_info, relation, life])
        csv_file.close()

    def parse(self, response):
        # if self.pointer == 0:
        #     self.download_html(response)

        items = BaikeItem()
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
        # 姓名和id
        items['name'] = urllib.parse.unquote(self.names_to_ids[self.ids[self.pointer]])
        items['id'] = self.ids[self.pointer]
        # 保存
        # self.save_csv(self.names_to_ids[self.ids[self.pointer]], summary, basic_info, relation, life)
        # self.save_json(self.names_to_ids[self.ids[self.pointer]], summary, basic_info, relation, life)
        yield items

        try:
            if self.pointer < self.counts:
                self.pointer += 1
                next_url = 'https://baike.baidu.com/item/' + self.names_to_ids[self.ids[self.pointer]] + '/' + self.ids[
                    self.pointer] + '?fromModule=lemma_search-box'
                yield scrapy.Request(url=next_url, callback=self.parse)
        except:
            return '没得爬了'
