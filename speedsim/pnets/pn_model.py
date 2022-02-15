import collections
import enum
import os
import tempfile

from graphviz import Digraph
from lxml import etree as ET
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

from pnets.attributes import ATTR_2_TYPE, INIT_COUNT, WEIGHT

JSON_TYPES = {
    'bool': bool,
    'str': str,
    'int': int,
    'float': float
}


class PnmlModel:
    """
    Petri net model. Contains places (buffers) and transiations (task nodes).
    All attributes are generic and may be added/removed.
    """

    # TODO: move predefined attributes here

    class Node:
        max_node_id = 0

        def __init__(self, marking, id=None):
            self._id = id if id is not None else "node" + str(PnmlModel.Node.max_node_id)
            PnmlModel.Node.max_node_id += 1
            self._marking = marking
            self._attributes = {}

        @property
        def id(self):
            return self._id

        @property
        def marking(self):
            """
            Node marking is used when rendering the node
            """
            return self._marking

        @marking.setter
        def marking(self, val):
            self._marking = val

        @property
        def attributes_dict(self):
            return self._attributes

        def set_attribute(self, key, value):
            self._attributes[key] = value

        def get_attribute(self, key, default=None):
            if key not in self._attributes:
                return default
            return self._attributes[key]

    class Place(Node):

        class Type(enum.Enum):
            START = 'start'
            END = 'end'
            BUFFER = 'buffer'

        def __init__(self, marking, type=Type.BUFFER, id=None, **attributes):
            super().__init__(marking, id=id)

            self._type = type
            for k, v in attributes.items():
                self.set_attribute(k, v)

        @property
        def is_start(self):
            return self._type == self.Type.START

        @property
        def is_end(self):
            return self._type == self.Type.END

        @property
        def type(self):
            return self._type

        @type.setter
        def type(self, type):
            self._type = type

    class Transition(Node):

        class Type(enum.Enum):
            WORKLOAD = 'WORKLOAD'
            TYPE = 'type'

        def __init__(self, marking, id=None, **attributes):
            super().__init__(marking, id=id)
            for k, v in attributes.items():
                self.set_attribute(k, v)

    class Arc:
        max_arc_id = 0

        def __init__(self, src, target, inscription='', id=None, **attributes):
            self._id = id if id is not None else "arc" + str(PnmlModel.Arc.max_arc_id)
            PnmlModel.Arc.max_arc_id += 1
            self._src = src
            self._target = target
            self._inscription = inscription
            self._attributes = {}
            self._attributes.update(**attributes)

        @property
        def id(self):
            return self._id

        @property
        def src(self):
            """
            Source item ID
            """
            return self._src

        @property
        def target(self):
            """
            Target item ID
            """
            return self._target

        @property
        def inscription(self):
            return self._inscription

        @inscription.setter
        def inscription(self, inscription):
            self._inscription = inscription

        @property
        def attributes_dict(self):
            return self._attributes

        def set_attribute(self, key, value):
            self._attributes[key] = value

        def get_attribute(self, key, default=None):
            if key not in self._attributes:
                return default
            return self._attributes[key]

    class Net:
        max_net_id = 0

        def __init__(self, places=None, transitions=None, arcs=None, id=None):
            self._id = id if id is not None else "net" + str(PnmlModel.Net.max_net_id)
            PnmlModel.Net.max_net_id += 1
            self._places = [] if places is None else list(places)
            self._transitions = [] if transitions is None else list(transitions)
            self._arcs = [] if arcs is None else list(arcs)

        @property
        def id(self):
            return self._id

        @property
        def transitions(self):
            return self._transitions

        @property
        def places(self):
            return self._places

        def get_transition(self, id):
            for trans in self._transitions:
                if trans.id == id:
                    return trans
            return None

        @property
        def arcs(self):
            return self._arcs

        def add_place(self, place):
            self._places.append(place)

        def add_transition(self, trans):
            self._transitions.append(trans)

        def add_arc(self, arc):
            self._arcs.append(arc)

        def get_place(self, place_id):
            for place in self._places:
                if place.id == place_id:
                    return place
            return None

        def get_arc(self, arc_id):
            for arc in self._arcs:
                if arc.id == arc_id:
                    return arc
            return None

        def get_arcs_by_target(self, target_name):
            """
            Returns a list of arcs by the target name
            :param target_name:
            :return: l
            """
            arcs = list()
            for arc in self._arcs:
                if arc.target == target_name:
                    arcs.append(arc)
            return arcs

    def __init__(self, nets=None):
        self._nets = [] if nets is None else list(nets)
        self._legend_str = ""
        self._attributes = {}

    def add_net(self, net):
        self._nets.append(net)

    @property
    def nets(self):
        return self._nets

    def get_net(self, id):
        for net in self._nets:
            if net.id == id:
                return net
        return None

    @property
    def attributes_dict(self):
        return self._attributes

    def set_attribute(self, key, value):
        self._attributes[key] = value

    def get_attribute(self, key, default=None):
        if key not in self._attributes:
            return default
        return self._attributes[key]

    def set_legend_str(self, legend_str):
        self._legend_str = legend_str

    def get_node(self, node_id):
        """
        Find place/transition specified by node_id
        :param node_id: node ID to find
        :return: Place/Transition or None
        """
        for net in self.nets:
            for place in net.places:
                if place.id == node_id:
                    return place
            for tran in net.transitions:
                if tran.id == node_id:
                    return tran
        return None

    def playback(self):
        """
        Playback PN model by injecting single token into all start nodes.
        Returns list of transition IDs as they were executed.
        """
        transitions = {tran.id: tran for net in self.nets for tran in net.transitions}
        places = {place.id: place for net in self.nets for place in net.places}
        tokens = collections.defaultdict(lambda: 0)
        incoming = collections.defaultdict(list)
        outgoing = collections.defaultdict(list)
        result = []

        for net in self.nets:
            for arc in net.arcs:
                incoming[arc.target].append(arc)
                outgoing[arc.src].append(arc)

        todo = []

        for place in places.values():
            if place.type == place.Type.START:
                tokens[place.id] = 1
                todo.append(place)
            else:
                tokens[place.id] = place.get_attribute(INIT_COUNT, 0)
                if tokens[place.id] > 0:
                    todo.append(place)

        def is_ready(tran):
            """
            Check if there are enough tokens to execute this transition
            """
            for arc in incoming[tran.id]:
                if tokens[arc.src] < arc.get_attribute(WEIGHT, 1):
                    return False
            return True

        def execute(tran):
            """
            Execute transition and subtract tokens from buffers
            """
            for arc in incoming[tran.id]:
                tokens[arc.src] -= arc.get_attribute(WEIGHT, 1)

            for arc in outgoing[tran.id]:
                tokens[arc.target] += arc.get_attribute(WEIGHT, 1)

            result.append(tran.id)

        while len(todo):
            place = todo.pop(0)
            for arc in outgoing[place.id]:
                tran = transitions[arc.target]
                changed = False
                while is_ready(tran):
                    execute(tran)
                    changed = True
                if changed:
                    for o in outgoing[tran.id]:
                        todo.append(places[o.target])

        return result

    def to_dag(self):
        """
        Convert PN model to networkx.DiGraph.
        Each node is a tuple (<transition-id>, <occurrence-id>).
        Edges represent dependencies between the occurrences of executed transitions
        :return: networkx.DiGraph
        """
        import networkx
        dag = networkx.DiGraph()  # collect dependencies between tasks to reduce number of generated constraints

        tasks = self.playback()

        incoming = collections.defaultdict(list)
        outgoing = collections.defaultdict(list)

        # transitions = {t.id: t for net in self.nets for t in net.transitions}
        places = {p.id: p for net in self.nets for p in net.places}

        for net in self.nets:
            for arc in net.arcs:
                incoming[arc.target].append(arc)
                outgoing[arc.src].append(arc)

        # dependency constraints:
        occs = collections.Counter()
        for task in tasks:
            index = occs[task]
            occs[task] += 1

            dag.add_node((task, index))

            if index > 0:
                dag.add_edge((task, index - 1), (task, index))

            for arc in incoming[task]:
                place = places[arc.src]
                if place.type == place.Type.START:
                    continue

                # current limitation: assert that each buffer has single incoming transition:
                assert len(incoming[place.id]) == 1
                arc2 = incoming[place.id][0]

                # handle dependency vs predecessor tasks:
                in_task = arc2.src
                if in_task == task:  # loop - TODO: add support for non 1-to-1 ratios
                    continue

                m = arc2.get_attribute(WEIGHT, 1)
                n = arc.get_attribute(WEIGHT, 1)
                in_inst_id = n * index // m + (n - 1)  # instance of the predecessor task

                dag.add_edge((in_task, in_inst_id), (task, index))

        return dag

    def _create_legend(self, graph):
        hw_to_show_in_legend = set()
        for net in self._nets:
            for transition in net.transitions:
                hw_to_show_in_legend.add(str(transition.get_attribute("hw_resource")))

        label = self._get_legend_html(hw_to_show_in_legend)
        graph.node("legend_id", label=label, labelloc='c', shape='none', labeljust="c", id='legend')
        graph.node("invisible_node", shape='none', style='invis', width='3', fixedsize='true', id='invis')

    def _add_transition_node(self, graph, transition):
        hw_resource = str(transition.get_attribute("hw_resource"))
        color_str = HW_RESOURCE[hw_resource].color if hasattr(HW_RESOURCE, hw_resource) else 'black'
        msg_size = transition.get_attribute("msg_size")
        comms_type= transition.get_attribute("comms_type")
        if msg_size is not None and msg_size > 0:
            label = self._get_html_description(str(transition.marking + "\n[msg_size (bytes): {}, comms_type: {}]".format(msg_size, comms_type)))
        else:
            label = self._get_html_description(str(transition.marking ))
        shape = "rectangle"
        if transition.get_attribute('type') == PnmlModel.Transition.Type.WORKLOAD:
            shape = "box3d"
        graph.node(transition.id, label=label, shape=shape, color=color_str,
                   style="setlinewidth(2)", id=transition.id)

    def _add_place_node(self, graph, place):
        shape = 'circle'
        if place.is_start:
            shape = 'invhouse'
        if place.is_end:
            shape = 'doubleoctagon'
        graph.node(place.id, label=str(place.marking), shape=shape, color='red', id=place.id)

    def _add_arc(self, graph, arc):
        graph.edge(str(arc.src), str(arc.target), label=str(arc.inscription), id=arc.id)

    def _split_nets(self):
        """
        Create list of sub-graphs from the model, each graph will be consist of up do THRESHOLD nodes.
        Used to render large pnmls by splitting the nets to svg files and assemble them manually.
        :return: List of graphs as binary data string
        """
        #  max number of place and transition nodes in each graph
        THRESHOLD = 500

        legend_graph = Digraph()
        self._create_legend(legend_graph)

        svgs = [legend_graph.pipe(format='svg')]
        todo = list(self.nets)
        while len(todo) > 0:
            nodes_count = 0
            graph = Digraph()
            while nodes_count < THRESHOLD:
                net = todo.pop(0)
                for transition in net.transitions:
                    self._add_transition_node(graph, transition)
                for place in net.places:
                    self._add_place_node(graph, place)
                for arc in net.arcs:
                    self._add_arc(graph, arc)
                nodes_count += len(net.transitions) + len(net.places)
                if len(todo) == 0:
                    break
            svgs.append(graph.pipe(format='svg'))

        return svgs

    def _split_nets_and_draw(self, file_name, format_=None):
        """
        split nets to graphs and draw (each graph will be consist of one or more nets)
        :param file_name: file path
        :return:
        """
        svg_width = 0
        svg_height = 0
        svg_view_box = [0.0] * 4
        net_elements = []
        translate_width = 4

        for graph in self._split_nets():
            root = ET.fromstring(graph)
            PnmlModel.remove_namespaces(root)
            width = int(root.attrib['width'][:-2])  # remove 'pt' suffix
            svg_width += width
            height = int(root.attrib['height'][:-2])  # remove 'pt suffix
            svg_height = height if height > svg_height else svg_height
            view_box = list(map(float, root.attrib['viewBox'].split(' ')))
            svg_view_box[2] += view_box[2]
            svg_view_box[3] = max(svg_view_box[3], view_box[3])
            for child in root:
                translate = child.attrib['transform'].split('translate')[1]
                translate_height = translate[1:-1].split(' ')[1]
                translate = 'translate(' + str(float(translate_width)) + ' ' + translate_height + ')'
                child.set('transform', 'scale(1 1) rotate(0) ' + translate)
                translate_width = svg_view_box[2] + 4
                net_elements.append(child)

        svg_attributes = {'width': str(svg_width) + 'pt',
                          'height': str(svg_height) + 'pt',
                          'viewBox': str(svg_view_box)[1:-1].replace(',', ''),
                          'xmlns': 'http://www.w3.org/2000/svg'}

        NSMAP = {'xlink': 'http://www.w3.org/1999/xlink'}

        svg_element = ET.Element('svg', attrib=svg_attributes, nsmap=NSMAP)
        svg_element.extend(net_elements)

        doc = ET.ElementTree(svg_element)
        doc.write(file_name)

        if format_ == 'pdf':
            drawing = svg2rlg(file_name)
            os.remove(file_name)
            file_name += '.pdf'
            renderPDF.drawToFile(drawing, file_name)
        else:
            os.rename(file_name, file_name + '.svg')
            file_name += '.svg'

        return file_name

    @staticmethod
    def remove_namespaces(element):
        if type(element.tag) == str and element.tag.startswith('{'):
            element.tag = element.tag.split('}', 1)[1]
            for attribute in element.attrib.keys():
                if attribute.startswith('{'):
                    new_attribute = attribute.split('}', 1)[1]
                    element[new_attribute] = element.attrib[attribute]
                    del element.attrib[new_attribute]
        for child in element:
            PnmlModel.remove_namespaces(child)

    def draw(self, file_name, view=False, format_=None, keep_gv=True):
        """
        Draw the PN net to an SVG or PDF file

        :param file_name: file name to write
        :param view: if True open viewer (browser)
        :param format_: either 'svg' or 'pdf'
        :param keep_gv: keep intermediate files
        :return: file name
        """

        SPLIT_THRESHOLD = 5000

        if format_ is None:
            base, ext = os.path.splitext(file_name)
            format_ = 'pdf' if ext == '.pdf' else 'svg'

        if file_name.endswith("." + format_):
            file_name, file_extension = os.path.splitext(file_name)

        if len(self.nets) > SPLIT_THRESHOLD:
            #  if we have over than SPLIT_THRESHOLD nets in the model, we draw the nets separately
            return self._split_nets_and_draw(file_name, format_=format_)

        graph = Digraph(format=format_)
        # FIXME: add options to speed up DOT rendering
        # graph.graph_attr['splines'] = 'false'
        # graph.graph_attr['nslimit'] = '1'
        # graph.graph_attr['nslimit1'] = '1'

        self._create_legend(graph)

        for net in self._nets:
            for transition in net.transitions:
                self._add_transition_node(graph, transition)

            for place in net.places:
                self._add_place_node(graph, place)

            for arc in net.arcs:
                self._add_arc(graph, arc)

        graph.render(file_name, view=view)
        if not keep_gv:
            try:
                os.remove(file_name)
            except OSError:
                pass

        render_file_name = file_name + '.' + str(format_)
        return render_file_name

    def save(self, file_name):
        """
        Save .pnml file
        :param file_name: file name of file-like object (such as io.BytesIO())
        """
        next_id = {0: 0}  # cannot be simple value

        def _next_id():
            next_id[0] += 1
            return next_id[0]
        # ID map is used to make sure we have consistent, unique IDs per .pnml file
        id_map = collections.defaultdict(_next_id)

        pnml_element = self._create_pnml_element()
        self._create_name_element(pnml_element, self._legend_str)

        for net in self._nets:
            net_element = self._create_net_element(pnml_element, net, id_map)

            for place in net.places:
                elem = self._create_node_element(net_element, place, 'place', id_map)
                elem.set('type', place.type.value)
            for transition in net.transitions:
                self._create_node_element(net_element, transition, 'transition', id_map)
            for arc in net.arcs:
                self._create_arc_element(net_element, arc, id_map)

        # write the tree to an xml file
        tree = ET.ElementTree(pnml_element)
        tree.write(file_name, pretty_print=True)

    @staticmethod
    def read(stream, attribute_types=ATTR_2_TYPE):
        """
        Read PNML model from a stream, return newly created PNML object
        :param stream: file-like object
        :param attribute_types: optional map of attribute names to type
        :return: PnmlModel
        """
        pnml = PnmlModel()

        etree = ET.parse(stream)
        pnml.set_legend_str(etree.find('name').find('text').text)

        # read tool-specific attributes:
        attr_element = etree.find("toolspecific")
        if attr_element is not None:
            pnml._attributes = pnml._read_attributes(attr_element, {})

        # read nets:
        for net_element in etree.findall('net'):
            tmp_net = pnml._element_to_net(net_element, attribute_types)
            pnml.add_net(tmp_net)
        return pnml

    def _element_to_net(self, net_element, attribute_types):
        """
        Read PnmlModel.Net from specified net XML element
        :return: PnmlModel.Net
        """
        tmp_net = PnmlModel.Net(id=net_element.get('id'))

        for place_element in net_element.findall('place'):
            initial_marking = place_element.find('initialMarking').find('text').text
            tmp_place = PnmlModel.Place(initial_marking, id=place_element.get('id'))
            if 'type' in place_element.attrib:
                tmp_place.type = PnmlModel.Place.Type(place_element.get('type'))

            attributes = self._read_attributes(place_element.find('toolspecific'), attribute_types)
            # WA for backward compatibility (04/06/2019)
            # Going forward "type" shouldn't be stored in attributes
            if 'type' in attributes:
                tmp_place.type = PnmlModel.Place.Type(attributes['type'])
                attributes.pop('type')
            tmp_place.attributes_dict.update(attributes)
            tmp_net.add_place(tmp_place)

        for transition_element in net_element.findall('transition'):
            tmp_transition = PnmlModel.Transition(transition_element.find('initialMarking').find('text').text,
                                                  id=transition_element.get('id'))

            attributes = self._read_attributes(transition_element.find('toolspecific'), attribute_types)
            tmp_transition.attributes_dict.update(attributes)
            tmp_net.add_transition(tmp_transition)

        for arc_element in net_element.findall('arc'):
            inscription = arc_element.find('inscription').find('text').text
            if not inscription:
                inscription = ''
            tmp_arc = PnmlModel.Arc(arc_element.get('source'),
                                    arc_element.get('target'), inscription, id=arc_element.get('id'))

            attributes = self._read_attributes(arc_element.find('toolspecific'), attribute_types)
            tmp_arc.attributes_dict.update(attributes)
            tmp_net.add_arc(tmp_arc)

        return tmp_net

    def _read_attributes(self, parent, attribute_types):
        """
        Read tool-specific attributes from the specified element
        :param parent: parent element
        :param attribute_types: predefined attribute types
        :return: dict
        """
        result = {}
        for child in parent:
            name = child.tag
            value = self._attribute_value(child, attribute_types)
            if value is not None:
                result[name] = value

        return result

    def _create_pnml_element(self):
        pnml_element = ET.Element('pnml')
        self._create_tool_specific_element(pnml_element, self.attributes_dict)
        return pnml_element

    def _create_net_element(self, parent, net, id_map):
        net_element = ET.SubElement(parent, 'net', {'id': str(id_map[net.id])})
        return net_element

    def _create_name_element(self, parent, name):
        name_element = ET.SubElement(parent, 'name')
        text_element = ET.SubElement(name_element, 'text')
        text_element.text = str(name)
        return name_element

    def _create_marking_element(self, parent, marking):
        marking_element = ET.SubElement(parent, 'initialMarking')
        text_element = ET.SubElement(marking_element, 'text')
        text_element.text = str(marking)
        return marking_element

    def _create_node_element(self, parent, node, element_type, id_map):
        node_element = ET.SubElement(parent, element_type, {'id': str(id_map[node.id])})
        self._create_name_element(node_element, "")
        self._create_marking_element(node_element, node.marking)
        self._create_tool_specific_element(node_element, node.attributes_dict)
        return node_element

    def _create_tool_specific_element(self, parent, attributes_dict):
        """
        Write object attributes to "toolSpecific" element of XML
        :param parent: parent XML Element
        :param attributes_dict: attributes dictionary
        :return: XML element with tool-specific attributes
        """
        result = ET.SubElement(parent, 'toolspecific', {'tool': 'speed'})
        for attribute, value in attributes_dict.items():
            if attribute in ATTR_2_TYPE:
                ET.SubElement(result, attribute, {'value': str(value)})
            else:
                self._value_to_element(result, attribute, value)

        return result

    def _value_to_element(self, parent, name, value):
        """
        Convert python value to an XML element with specified tag. If the item is not a dict or a list,
        then the function will create
        an xml element of te form <item name=name value=value type=type(value)>.
        If the name is None then the name attribute will be removed from the xml element.

        :param tag: XML tag to use for the element
        :param value: value to convert
        """
        if isinstance(value, dict):
            self._json_to_element(ET.SubElement(parent, name or 'item', {'type': 'json'}), value)
        elif isinstance(value, list):
            self._list_to_element(ET.SubElement(parent, name or 'item', {'type': 'list'}), value)
        else:
            done = False
            for t_name, t_type in JSON_TYPES.items():
                if isinstance(value, t_type):
                    if parent is not None and parent.get('type') in ['json', 'list']:
                        d = {} if name is None else {'name': name}
                        d.update({'value': str(value), 'type': t_name})

                        ET.SubElement(parent, 'item', d)
                    else:
                        ET.SubElement(parent, name, {'value': str(value), 'type': t_name})
                    done = True
                    break
            if not done:
                raise ValueError("Unknown value type for {}".format(value))

    def _list_to_element(self, parent, items):
        """
        Convert list of values to XML.
        :param parent: parent XML node representing the list.
        :param items: list values
        :return: parent
        """
        for val in items:
            self._value_to_element(parent, None, val)

    def _json_to_element(self, parent, json_dict):
        """
        Convert JSON dictionary to XML
        :param parent: parent XML Element
        :param json_dict: dictionary with values
        """
        for key, value in json_dict.items():
            assert isinstance(key, str)
            self._value_to_element(parent, key, value)

    def _element_to_json(self, elem):
        """
        Parse XML into a JSON object
        :param elem: parent XML element
        :return: dict
        """
        result = {}
        for child in elem:
            value = self._attribute_value(child, {})
            if value is not None:
                result[child.get('name')] = value
        return result

    def _element_to_list(self, elem):
        """
        Read list of values from the XML element
        :param elem: parent XML element
        :return: list
        """
        return [self._attribute_value(child, {}) for child in elem]

    def _attribute_value(self, child, attribute_types):
        """
        Extract attribute values from XML element
        :param child: XML element
        :param attribute_types:
        :return:
        """
        if child.tag in attribute_types:
            return attribute_types[child.tag](child.get('value'))

        value_type = child.get('type')
        if value_type == 'json':
            return self._element_to_json(child)
        elif value_type == 'list':
            return self._element_to_list(child)
        else:
            for t_name, t_type in JSON_TYPES.items():
                if t_name == value_type:
                    return t_type(child.get('value'))
            print("-W- Unknown attribute type for {}: {}".format(child.tag, value_type))
            return child.get('value')  # default to str() representation

    def _create_arc_element(self, parent, arc, id_map):
        arc_element = ET.SubElement(parent, 'arc',
                                    {'id': str(id_map[arc.id]),
                                     'source': str(id_map[arc.src]),
                                     'target': str(id_map[arc.target])})
        self._create_inscription_element(arc_element, arc.inscription)
        self._create_tool_specific_element(arc_element, arc.attributes_dict)
        return arc_element

    def _create_inscription_element(self, parent, inscription):
        inscription_element = ET.SubElement(parent, 'inscription')
        text_element = ET.SubElement(inscription_element, 'text')
        text_element.text = str(inscription)
        return inscription_element

    def _get_legend_html(self, hw_to_show):
        if self._legend_str is None or self._legend_str == "":
            return ""

        task_prop_label, trace_info_label = self._split_legend_label(str(self._legend_str).split("\n"))
        color_legend_label = self._get_color_table(hw_to_show)

        label = '<<table border="0"><tr><td>' \
                '<table border="1" cellpadding="3">' + task_prop_label + '</table></td></tr>' \
                '<tr><td border="0" colspan="2" rowspan="1"> </td></tr>' \
                '<tr><td><table border="1" cellpadding="3">' + trace_info_label + '</table></td></tr>' \
                + '<tr><td border="0" colspan="2" rowspan="1"> </td></tr>' \
                '<tr><td><table border="1" cellpadding="3" cellspacing="4">'\
                + color_legend_label + '</table></td></tr></table>>'
        return label

    def _get_scene_legend_html(self, hw_to_show):
        task_prop_label, trace_info_label = self._split_scene_legend_label(str(self._legend_str).split("\n"))
        color_legend_label = self._get_color_table(hw_to_show)
        labels = []
        label_1 = '<table border="0"><tr><td><table border="0" cellpadding="3" align="center">'\
                  + task_prop_label + '</table></td></tr>'
        label_2 = '<tr><td><table border="0" cellpadding="3" align="center">' + trace_info_label + '</table></td></tr>'
        label_3 = '<tr><td><table border="0" cellpadding="3" cellspacing="4" align="center">'\
                  + color_legend_label + '</table></td></tr></table>'
        labels.extend([label_1, label_2, label_3])
        return labels

    @staticmethod
    def _split_scene_legend_label(lines_list):
        task_prop_label = ''
        trace_info_label = ''
        labels = [task_prop_label, trace_info_label]
        i = 0
        for nodes in lines_list:
            if 'Trace Info' in nodes:
                i += 1
            for node in nodes.split("\n"):
                labels[i] += '<tr>'
                if 'CPU Runtime {min, avg, max}' in node:
                    labels[i] += '<td align="left" border="0">' + node.split("{")[0] + \
                             '</td><td align="left" border="0">{' + node.split("{")[1].split(":")[0] + ','\
                             + node.split("{")[1].split(":")[1] + '</td>'
                else:
                    for line in node.split(":", 1):
                        if line == 'Task Properties' or line == 'Trace Info':
                            labels[i] += '<td align="center" colspan="2" border="0">' + line + '<br/></td>'
                        else:
                            labels[i] += '<td align="left" border="0">' + line + '</td>'
                labels[i] += '</tr>'
        return labels[0], labels[1]

    @staticmethod
    def _split_legend_label(lines_list):
        task_prop_label = ''
        trace_info_label = ''
        labels = [task_prop_label, trace_info_label]
        i = 0
        for nodes in lines_list:
            if 'Trace Info' in nodes:
                i += 1
            for node in nodes.split("\n"):
                labels[i] += '<tr><td border="0"></td>'
                if 'CPU Runtime {min, avg, max}' in node:
                    labels[i] += '<td align="left" border="0">' + node.split("{")[0] + \
                             '</td><td align="left" border="0">{' + node.split("{")[1].split(":")[0] + ','\
                             + node.split("{")[1].split(":")[1] + '</td>'
                else:
                    for line in node.split(":", 1):
                        if line == 'Task Properties' or line == 'Trace Info':
                            labels[i] += '<td align="center" colspan="2" border="0">' + line + '<br/></td>'
                        else:
                            labels[i] += '<td align="left" border="0">' + line + '</td>'
                labels[i] += '<td border="0"></td></tr>'
        return labels[0], labels[1]

    @staticmethod
    def _get_html_description(transition_marking):
        body = '<font point-size="8"><br/></font>'
        for line in transition_marking.split("\n")[1:]:
            body += line + '<font point-size="8"><br/><br/></font>'
        label = '<<table border="0" cellborder="0"><tr><td><font point-size="18">' \
                + transition_marking.split("\n")[0] + '</font></td></tr><tr><td><font point-size="13">' \
                + body + '</font></td></tr></table>>'
        return label

    @staticmethod
    def _get_scene_html_description(transition_marking):
        body = '<font point-size="8"><br/></font>'
        for line in transition_marking.split("\n")[1:]:
            body += line + '<font point-size="8"><br/></font>'
        label = '<<table border="0" cellborder="0"><tr><td align = "center"><font point-size="18">' \
                + transition_marking.split("\n")[0] + \
                '</font></td></tr><tr><td align = "center"><font point-size="13">' + body + '</font></td></tr></table>>'
        return label

    @staticmethod
    def _get_color_table(hw_to_show):
        if not hw_to_show:
            hw_to_show = HW_RESOURCE.__members__.keys()
        label = '<tr><td border="0" colspan="2">Color Legend</td></tr>'
        for hw_item in HW_RESOURCE:
            if hw_item.value not in hw_to_show:
                continue
            label += '<tr><td border="0" align="center" bgcolor="' + hw_item.color + '">' \
                     '<font point-size="8"> </font></td><td border="0" align="left" cellpadding="4">' \
                     '<font point-size="12">' + hw_item.value + '</font></td></tr>'

        return label

    def _repr_svg_(self):
        """
        Jupyter integration. This will be called by Jupyter to display the object.
        :return: svg code
        """
        fd, tmp_file = tempfile.mkstemp(".svg")
        os.close(fd)
        self.draw(tmp_file, format_='svg', view=False)
        with open(tmp_file, 'r') as stream:
            text = stream.read()
        os.unlink(tmp_file)
        return text


def get_attribute_type(attribute, attribute_types):
    """
    Return type of pre-defined attributes

    :param attribute: attribute name
    :param attribute_types: dict of name -> type
    """
    if attribute not in attribute_types:
        raise (Exception("The type of the attribute %s is not defined" % attribute))
    return attribute_types[attribute]


class HW_RESOURCE(enum.Enum):
    """
    | Supported HW resource types.
    | Each enum value has 'value', 'name' and 'color' attributes
    """
    CPU = ('CPU', 'black')
    GT_GFX = ('GT_GFX', 'darkgreen')
    GT_MEDIA = ('GT_MEDIA', 'blue')
    DISK = ('DISK', 'orange')
    TIMER = ('TIMER', 'darkgrey')
    OTHER = ('CPU', 'black')  # ToDo: Discuss what this should be

    def __new__(cls, value, color):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.color = color
        return obj


class DISK_OPERATION(enum.Enum):
    """
    Disk operation types
    """
    READ = 'READ'
    WRITE = 'WRITE'
    FLUSH = 'FLUSH'
