from itertools import permutations
from pnets import PnmlModel
from collections import namedtuple

class Fabric:
    EndPoint = namedtuple("EndPoint", ['node', 'tile', 'gpu'], defaults=[0])
    MsgTransaction = namedtuple("MsgTransaction", ['id', 'source', 'destination', 'comm_type', 'msg_type', 'size'])

    def __init__(self, name, ignore_exception=True):
        self._name = name
        # lowest level of granularity can be a node or tile or gpu
        self._endpoints = []
        # records message transaction between two endpoints
        self._msg_transactions = []
        self._ignore_exception = ignore_exception

    def add_endpoint(self, endpoint: EndPoint):
        for ep in self._endpoints:
            if ep.node == endpoint.node and ep.tile == endpoint.tile and ep.gpu == endpoint.gpu:
                if not self._ignore_exception:
                    raise ValueError("Endpoint with same node, tile, gpu exists!!")
                else:
                    print("Endpoint with same node, tile, gpu exists!!")
                    return
        self._endpoints.append(endpoint)

    def add_msg_transaction(self, msg_trans: MsgTransaction):
        for mt in self._msg_transactions:
            if mt.id == msg_trans.id:
                if not self._ignore_exception:
                    raise ValueError("Message transaction with id exists!!")
                else:
                    print("Message transaction with id exists!!")
                    return
        self._msg_transactions.append(msg_trans)

    def to_pnml_model(self):
        """
        Converting fabric to pnml model
        :return:  Pnml model
        """

        def _get_ep_name(endpoint):
            sep = "_"
            return sep.join([str(endpoint.node), str(endpoint.tile), str(endpoint.gpu)])

        def _get_buffer_id(msg_transaction):
            return str(msg_transaction.id) + _get_ep_name(msg_transaction.source) + "__" + \
                   _get_ep_name(msg_transaction.destination) + "__p"

        net = PnmlModel.Net(transitions=[], places=[], arcs=[])

        for endpoint in self._endpoints:
            tran = PnmlModel.Transition(_get_ep_name(endpoint),
                                        id=_get_ep_name(endpoint),
                                        node=endpoint.node,
                                        tile=endpoint.tile,
                                        gpu=endpoint.gpu)
            net.add_transition(tran)

        for msg_transaction in self._msg_transactions:
            place = PnmlModel.Place("b", id=_get_buffer_id(msg_transaction))
            net.add_place(place)
            net.add_arc(PnmlModel.Arc(_get_ep_name(msg_transaction.source), place.id,
                                      id="pre__" + _get_ep_name(msg_transaction.source) + "__" + \
                                         _get_ep_name(msg_transaction.destination),
                                      comm_type=msg_transaction.comm_type,
                                      msg_type=msg_transaction.msg_type,
                                      msg_size=msg_transaction.size))

            net.add_arc(PnmlModel.Arc(place.id, _get_ep_name(msg_transaction.destination),
                                      id="post__" + _get_ep_name(msg_transaction.source) + "__" + \
                                         _get_ep_name(msg_transaction.destination),
                                      comm_type=msg_transaction.comm_type,
                                      msg_type=msg_transaction.msg_type,
                                      msg_size=msg_transaction.size))
        return PnmlModel([net])

    def draw(self, file_name, view=False, format_="svg", keep_gv=False):
        """
        Drawing system platform

        :param file_name:
        :param view:
        :param format_:
        :param keep_gv:
        :return:
        """
        pnml_model = self.to_pnml_model()
        pnml_model.save(file_name + ".pnml")
        return pnml_model.draw(file_name, view=view, format_=format_, keep_gv=keep_gv)


def find_node_num(nodes, tile):
    for node, tile_list in nodes.items():
        if tile in tile_list:
            return node
    raise Exception("Error!!")


def trace_print(trace_fp, nodes, comms_tuple_list, msg_type, comm_type, msg_id_start, fabric):
    msg_id = msg_id_start
    if not trace_fp:
        print("Trace fp not set")
        return

    for tup in comms_tuple_list:
        source = fabric.EndPoint(find_node_num(nodes, tup[0]), tup[0], 0)
        dest = fabric.EndPoint(find_node_num(nodes, tup[1]), tup[1], 0)
        fabric.add_endpoint(source)
        fabric.add_endpoint(dest)

        msg_size = 45465
        msg_transaction = fabric.MsgTransaction(msg_id, source, dest, comm_type, msg_type, msg_size)
        msg_id += 1
        fabric.add_msg_transaction(msg_transaction)
        trace_fp.write("Source=(Node={}, Tile={}), Dest=(Node={}, Tile={}),"
                       " Msg_type={}, Comm_type={}, Size={}\n".format(find_node_num(nodes, tup[0]),
                                                                    tup[0],
                                                                    find_node_num(nodes, tup[1]),
                                                                    tup[1],
                                                                    msg_type,
                                                                    comm_type,
                                                                    msg_size))
    return msg_id


def nw_traffic_gen(num_nodes, num_tiles_per_node, model_split=1):
    nodes = {}
    for node_num in range(0, num_nodes):
        nodes[node_num] = list(range(node_num * num_tiles_per_node,
                                     (node_num + 1) * num_tiles_per_node, 1))
    wt_scaleup = []
    wt_scaleout = []
    fwd_inp_scaleup = []
    fwd_inp_scaleout = []

    if model_split > 1:
        if model_split <= num_tiles_per_node:  # in this case you will divide nodes into subnodes
            for node_num in range(0, num_nodes):
                SubNodes = {}
                for sub_node in range(0, int(num_tiles_per_node / model_split)):
                    # below line divides the Node into Sub nodes
                    sub_node_tile_list = nodes[node_num][sub_node * model_split:(sub_node + 1) * model_split]
                    fwd_inp_scaleup += list(permutations(sub_node_tile_list, 2))  # within given subnode
                    SubNodes[sub_node] = sub_node_tile_list  # first construct all subnodes for wt scaleup

                for sub_node_idx in range(0, model_split):  # iterate over number of tiles in each subnode
                    scaleup_comm_node = []
                    for sub_node_num, tile_list in SubNodes.items():
                        scaleup_comm_node.append(tile_list[sub_node_idx])  # tiles communicating accross subnodes
                    wt_scaleup += list(permutations(scaleup_comm_node, 2))

                for tile_idx in range(0, num_tiles_per_node):
                    scaleout_comm_nodes = []
                    for node_num, tile_list in nodes.items():
                        scaleout_comm_nodes.append(tile_list[tile_idx])
                    wt_scaleout += list(permutations(scaleout_comm_nodes, 2))

        else:  # in this case you will merge two nodes to form a mega node
            for node_num in range(0, num_nodes):
                fwd_inp_scaleup += list(permutations(nodes[node_num], 2))

            mega_nodes = {}
            nodes_per_mega_node = int(model_split / num_tiles_per_node)
            for mega_node_idx in range(0, int((num_nodes * num_tiles_per_node) / model_split)):
                mega_nodes[mega_node_idx] = list(nodes.keys())[mega_node_idx * nodes_per_mega_node:
                                                               (mega_node_idx + 1) * nodes_per_mega_node]
                for tile_idx in range(0, num_tiles_per_node):
                    scaleout_comm_nodes = []
                    for node_num in mega_nodes[mega_node_idx]:
                        scaleout_comm_nodes.append(nodes[node_num][tile_idx])  # Fwd and inp scaleout within mega node
                    fwd_inp_scaleout += list(permutations(scaleout_comm_nodes, 2))

            for tile_idx in range(0, nodes_per_mega_node * num_tiles_per_node):
                scaleout_comm_nodes = []
                for mega_node_num, node_list in mega_nodes.items():
                    tile_list = []
                    for node in node_list:
                        tile_list += nodes[node]
                    scaleout_comm_nodes.append(tile_list[tile_idx])
                wt_scaleout += list(permutations(scaleout_comm_nodes, 2))

    else:
        for node_num in range(0, num_nodes):
            wt_scaleup += list(permutations(nodes[node_num], 2))

        for tile_idx in range(0, num_tiles_per_node):
            scaleout_comm_nodes = []
            for node_num, tile_list in nodes.items():
                scaleout_comm_nodes.append(tile_list[tile_idx])
            wt_scaleout += list(permutations(scaleout_comm_nodes, 2))

    msg_id = 0
    # with open("allreduce_sup_a2a_so_a2a_trace.txt", "w") as fp:
        # fabric = Fabric("allreduce_sup_a2a_so_a2a")
        # msg_id = trace_print(fp, nodes, wt_scaleup, "wt", "scaleup", msg_id, fabric)
        # msg_id = trace_print(fp, nodes, wt_scaleout, "wt", "scaleout", msg_id, fabric)
        # msg_id = trace_print(fp, nodes, fwd_inp_scaleup, "fwd", "scaleup", msg_id, fabric)
        # msg_id = trace_print(fp, nodes, fwd_inp_scaleup, "inp", "scaleup", msg_id, fabric)
        # msg_id = trace_print(fp, nodes, fwd_inp_scaleout, "fwd", "scaleout", msg_id, fabric)
        # msg_id = trace_print(fp, nodes, fwd_inp_scaleout, "inp", "scaleout", msg_id, fabric)
        # fabric.draw("allreduce_sup_a2a_so_a2a", format_="pdf")
    return wt_scaleup, wt_scaleout, fwd_inp_scaleup, fwd_inp_scaleout
