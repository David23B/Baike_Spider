import networkx as nx
import matplotlib.pyplot as plt

G = nx.Graph()  # 创建一个无向图
G.add_node("蔡徐坤")
G.add_nodes_from(["白鹿", "赖锦标"])
G.add_edges_from([("蔡徐坤", '白鹿'), ('赖锦标', '蔡徐坤')])
G.graph['name'] = 'relation_graph'
G.nodes['蔡徐坤']['id'] = 123
G.nodes['蔡徐坤']['summary'] = "蔡徐坤的人物简介"
G.nodes['蔡徐坤']['relation'] = {'父亲': ['赖锦标'], '搭档': ['白鹿', '陈立农']}
G.edges[('赖锦标', '蔡徐坤')]['relation'] = '父子'
G.edges[("蔡徐坤", '白鹿')]['relation'] = '搭档'
G.add_node("蔡徐坤")
print(G.nodes)

# draw graph with labels
plt.figure(3, figsize=(25, 25)) # 这里控制画布的大小，可以说改变整张图的布局
plt.subplot(111)
pos = nx.spring_layout(G, iterations=20)
# nx.draw(G1_LCC, node_color="red", edge_color="grey", node_size="20")
nx.draw(G, pos,edge_color="grey", node_size=500) # 画图，设置节点大小
# node_labels = nx.get_node_attributes(G, 'name')  # 获取节点的desc属性
nx.draw_networkx_labels(G, pos,font_size=50,font_family='SimHei')  # 将desc属性，显示在节点上
edge_labels = nx.get_edge_attributes(G, 'relation') # 获取边的name属性，
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,font_size=50,font_family='SimHei') # 将name属性，显示在边上
# 检测圆环
print(nx.cycle_basis(G.to_undirected()))
# plt.savefig('./tu.pdf')
plt.show()
