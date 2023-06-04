import os
from pathlib import Path

import scrapy
from ..items import BaikeItem
import json
import re
import requests
import urllib
import csv
from collections import defaultdict

import community
import networkx as nx
import matplotlib.pyplot as plt

class BaiduSpider(scrapy.Spider):
    name = 'baidu'
    person = input("请输入名字：")
    counts = int(input("请输入需要爬取的人数："))
    names_to_ids = {}
    ids = []
    pointer = 0
    allowed_domains = ['baike.baidu.com']
    start_urls = ['https://baike.baidu.com/item/' + person, ]

    G = nx.Graph()  # 实例化一个无向图

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
                self.G.add_node(f'{id}')
                self.G.nodes[f'{id}']['name'] = urllib.parse.unquote(name)
            rela_url = 'https://baike.baidu.com/starmap/api/gethumanrelationcard?lemmaId=' + id + '&lemmaTitle=' + name
            # print(rela_url)
            relation = requests.get(rela_url).json()['list']
            if relation:
                for rel in relation:
                    final_relation[rel['relationName']].append(rel['lemmaTitle'])
                    if str(rel['lemmaId']) not in self.ids:
                        self.names_to_ids[str(rel['lemmaId'])] = urllib.parse.unquote(rel['lemmaTitle'])
                        self.ids.append(str(rel['lemmaId']))
                        self.G.add_node(f'{str(rel["lemmaId"])}')
                        self.G.nodes[f'{str(rel["lemmaId"])}']['name'] = urllib.parse.unquote(rel['lemmaTitle'])
                        self.G.add_edge(id, str(rel["lemmaId"]))
                        self.G.edges[(id, str(rel["lemmaId"]))]['relationName'] = rel['relationName']
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

    def save_graph_attributes(self, id, summary, basic_info, relation, life):
        self.G.nodes[id]['summary'] = summary
        self.G.nodes[id]['basic_info'] = str(basic_info).replace('\'', '').replace('{', '').replace('}', '')
        self.G.nodes[id]['relation'] = str(relation)[29:-2].replace('\'', '')
        self.G.nodes[id]['biography'] = str(life).replace('\'', '').replace('[', '').replace(']', '')

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
        self.save_graph_attributes(self.ids[self.pointer], summary, basic_info, relation, life)
        self.save_csv(self.names_to_ids[self.ids[self.pointer]], summary, basic_info, relation, life)
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

    def close(self, spider, reason):
        if len(self.ids) > 0:
            nx.write_gexf(self.G, "baike.gexf")
            partition = community.best_partition(self.G)  # 字典类型
            size = float(len(set(partition.values())))  # 社区数
            pos = nx.spring_layout(self.G)  # 美化
            count = 0.
            core_nodes = []  # 核心人物节点
            for com in set(partition.values()):
                count = count + 1.
                list_nodes = [nodes for nodes in partition.keys() if partition[nodes] == com]
                max_degree = self.G.degree(list_nodes[0])
                max_degree_node = list_nodes[0]
                for dian in list_nodes:
                    if self.G.degree(dian) > max_degree:
                        max_degree = self.G.degree(dian)
                        max_degree_node = dian
                list_nodes.remove(max_degree_node)
                core_nodes.append(max_degree_node)
                nx.draw_networkx_nodes(self.G, pos, list_nodes, node_size=20, node_color=str(0.5))
            for i, core in enumerate(core_nodes):
                print(f'第{i+1}个核心人物: {self.G.nodes[core]["name"]}')
            nx.draw_networkx_nodes(self.G, pos, core_nodes, node_size=50, node_color=str(0))
            nx.draw_networkx_edges(self.G, pos, alpha=0.5)
            plt.show()
            # 在已经爬到的人物中找两个人的关系
            while(1):
                while(1):
                    person_a = input("请输入第一个人名：")
                    a_id = -1
                    for node in partition.keys():
                        if self.G.nodes[node]["name"] == person_a:
                            a_id = node
                            break
                    if a_id == -1:
                        print("该人物不在人物图中")
                    else:
                        break
                while(1):
                    person_b = input("请输入第二个人名：")
                    b_id = -1
                    for node in partition.keys():
                        if self.G.nodes[node]["name"] == person_b:
                            b_id = node
                            break
                    if b_id == -1:
                        print("该人物不在人物图中")
                    else:
                        break
                if not nx.has_path(self.G, a_id, b_id):
                    print("这两人物没有任何关联")
                    continue
                else:
                    relation_list = nx.shortest_path(self.G, a_id, b_id)
                    centence = str(self.G.nodes[b_id]["name"])+'是'+str(self.G.nodes[a_id]["name"])
                    for i in range(len(relation_list)-1):
                        ship = self.G.edges[(relation_list[i], relation_list[i+1])]["relationName"]
                        centence = centence + '的' + str(ship)
                    print(centence)
                break
        else:
            print("没有爬到任何人物")
