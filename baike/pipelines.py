# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymysql

# 连接数据库
def dbHandle():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="nevergiveup23",
        port=3306,
        charset="utf8",
        use_unicode=False
    )
    return conn


class BaikePipeline:
    def process_item(self, item, spider):
        dbObject = dbHandle()
        cursor = dbObject.cursor()
        cursor.execute('use baike_spider')
        # 无论数据类型是什么，value中都用%s
        sql = "INSERT INTO `baike`(`id`,`name`,`summary`,`basic_info`,`relation`,`biography`) VALUES(%s,%s,%s,%s,%s,%s)"
        try:
            cursor.execute(sql, (int(item['id']), str(item['name']), str(item['summary']),
                                 str(item['basic_info']).replace('\'', '').replace('{', '').replace('}', ''),
                                 str(item['relation'])[29:-2].replace('\'', ''),
                                 str(item['biography']).replace('\'', '').replace('[', '').replace(']', '')))
            cursor.connection.commit()
        except BaseException as e:
            print("错误在这里>>>>>>>>>>>>>", e, "<<<<<<<<<<<<<错误在这里")
            dbObject.rollback()
        return item
