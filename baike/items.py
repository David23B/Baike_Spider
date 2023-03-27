# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BaikeItem(scrapy.Item):
    # define the fields for your item here like:
    name = scrapy.Field()  # 人名
    summary = scrapy.Field()  # 简介
    basic_info = scrapy.Field()  # 基本信息
    biography = scrapy.Field()  # 人物生平
    relation = scrapy.Field()  # 人物关系

    pass
