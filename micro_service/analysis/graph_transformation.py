import json
import copy


def twox_fwd_pass(graph_json):
    """
    modify json to add new nodes for fwd pass, simulates checkpoint implementation
    """

    successor_dict = {}
    predecessor_dict = {}

    for link in (graph_json["links"]):
        source = link['source']
        dst = link['target']
        if source not in successor_dict.keys():
            successor_dict[source] = []
        successor_dict[source].append(dst)
        if dst not in predecessor_dict.keys():
            predecessor_dict[dst] = []
        predecessor_dict[dst].append(source)
    start_layers = list(successor_dict.keys() - predecessor_dict.keys())
    nodes2replicate = {}

    node_count = len(graph_json['nodes'])
    for layer in graph_json['nodes']:
        layer_pass = layer['data']['Layer']['l_pass']
        layer_name = layer['data']['Layer']['Layer Name']
        if layer_pass == "fwd" or layer_pass == "oth":
            layer_2x = copy.deepcopy(layer)
            layer_2x['data']['Layer']['Layer Name'] = "2_" + layer_name
            layer_2x['label'] = "2_" + layer_2x['label']
            layer_2x['id'] = node_count
            node_count += 1
            nodes2replicate[layer['id']] = layer_2x

    for id, layer in nodes2replicate.items():
        graph_json['nodes'].append(layer)

    links2replicate = {}
    links2remove = []

    for link in (graph_json["links"]):
        src = link['source']
        dst = link['target']
        if src in nodes2replicate.keys() and dst in nodes2replicate.keys():
            link_2x = copy.deepcopy(link)
            link_2x['source'] = nodes2replicate[src]['id']
            link_2x['target'] = nodes2replicate[dst]['id']
            key = "{}_{}".format(nodes2replicate[src]['id'],
                                 nodes2replicate[dst]['id'])
            links2replicate[key] = link_2x
        elif src in nodes2replicate.keys():
            link_2x = copy.deepcopy(link)
            link_2x['source'] = nodes2replicate[src]['id']
            link_2x['target'] = dst
            #print(link_2x['source'], link_2x['target'])
            key = "{}_{}".format(nodes2replicate[src]['id'], dst)
            links2replicate[key] = link_2x
            links2remove.append(link)
            for start in start_layers:
                link_rewire = copy.deepcopy(link)
                link_rewire['target'] = nodes2replicate[start]['id']
                key = "{}_{}".format(src, nodes2replicate[start]['id'])
                links2replicate[key] = link_rewire

    for link in links2remove:
        graph_json["links"].remove(link)

    for key, link in links2replicate.items():
        graph_json["links"].append(link)

    return graph_json
