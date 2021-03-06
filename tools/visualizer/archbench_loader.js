function layerLabelHTML(node, layer, class_type = 'layer') {
    let label = "<table class='" + class_type + "'>";
    for(const [title, value] of Object.entries(layer)) {
        let final_value = value;

        if(Array.isArray(final_value)) {
            let values = [];
            for(const sub of final_value) {
                if(typeof(sub) == 'object') {
                   if('Tensor' in sub) {
                       values.push(sub.Tensor.name + "(" + sub.Tensor.dims + ")");
                   }
                }
                else {
                    values.push(sub);
                }
            }
            final_value = values.join('<br />');
        }

        label += "<tr><td>" + title + "</td><td>" + final_value + "</td></tr>";
    }
    label += "</table>";

    if('contraction' in node) {
       for(const [index, value] of Object.entries(node.contraction)) {
          label += layerLabelHTML(value, value.data.Layer, 'contraction');
       }
    }

    return label;
}

function nodeLabelHTML(node) {
    node.labelType = 'html';

    if('data' in node) {
        if('Layer' in node.data) {
            node.label = layerLabelHTML(node, node.data.Layer);
        } else if('Data' in data) {
           data = node.data.Data;
        }
    }
    else if('type' in node && node.type == "GlobalInput") {
        node.label = "<table class='data'>";
        node.label += "<tr><td>ID</td><td>" + node.id + "</td></tr>"
        node.label += "<tr><td>Name</td><td>" + node.name + "</td></tr>"
        node.label += "<tr><td>type</td><td>" + node.type + "</td></tr>"
        node.label += "<tr><td>dims</td><td>" + node.dims + "</td></tr>"
        node.label += "</table>";
    }
    else {
        node.label = "<table class='layer'>";
        node.label += "<tr><td>ID</td><td>" + node.id + "</td></tr>";
        node.label += "<tr><td>Name</td><td>" + node.name + "</td></tr>";
        node.label += "<tr><td>Type</td><td>" + node.type + "</td></tr>";
        if('run' in node) {
            node.label += "<tr><td>Run</td><td>" + node.run + "</td></tr>";
        }
        node.label += "<tr><td>Op</td><td>" + node.op + "</td></tr>";
        if('params' in node) {
            node.label += "<tr><table class='params'>";
            for(const [key, value] of Object.entries(node.params)) {
                node.label += "<tr><td>" + key + "</td><td>" + value + "</td></tr>";
            }
            node.label += "</table></tr>";
        }
        if('contraction' in node) {
            for(const contraction of node.contraction) {
                node.label += "<tr><table class='contraction'>";
                node.label += "<tr><td>Name</td><td>" + contraction.name + "</td></tr>";
                node.label += "<tr><td>Type</td><td>" + contraction.type + "</td></tr>";
                node.label += "<tr><td>Op</td><td>" +   contraction.op + "</td></tr>";
                node.label += "</table></tr>"
            }
        }

        node.label += "</table>";
    }
}

function layerLabelSVG(node) {
    xmlns = 'http://www.w3.org/2000/svg';

    let g = document.createElementNS(xmlns, 'g');

    let rect = document.createElementNS(xmlns, 'rect');
    rect.setAttribute('rx', '15');
    g.appendChild(rect);

    let text = document.createElementNS(xmlns, 'text');
    text.setAttribute('font-size', '20');
    text.setAttribute('font-family', 'Verdana');
    text.setAttribute('fill', 'black');
    text.setAttribute('x', '5');
    text.setAttribute('y', '20');
    text.innerHTML = node.data.Layer["Layer Name"];
    g.appendChild(text); 

    rect.setAttribute('width', 20 * text.innerHTML.length);
    node.shape = 'none';
    node.labelType = 'svg';
    node.label = g;
}

function loadGraph(data) {
    var g = new dagreD3.graphlib.Graph({directed: true, multigraph: true}).setGraph({})

    g.setDefaultEdgeLabel(
        function(v, w, key) {
            if ('label' in data.links[key]) {
                return data.links[key].label;
            }
            return key;
        }
    );

    for(const [index, node] of Object.entries(data.nodes)) {
        if(node != null) {
            delete node.weight;
            g.setNode(node.id, node);
            nodeLabelHTML(node);
            // layerLabelSVG(node);
        } else {
            console.log("Node unreadable", index, node);
        }
    }

    for(const [index, edge] of Object.entries(data.links)) {
        if(edge != null) {
            // Weight appears to have an impact over the drawing mechanics. Need to rethink this.
            delete edge.weight;
            g.setEdge(edge.source, edge.target, edge, index);
        } else {
            console.log("Edge unreadable", index, edge);
        }
    }

    return g 
}

graph = loadGraph(graph_data);

var svg = d3.select("svg")
var inner = svg.select("g")
var zoom = d3.zoom().on("zoom", function() {
        inner.attr("transform", d3.event.transform);
    }
);
svg.call(zoom);

var render = new dagreD3.render();
render.shapes().none = function(parent, bbox, node) {
    var w = bbox.width;
    var h = bbox.height;
    var points = [
        {x: 0, y: 0},
        {x: w, y: 0}, 
        {x: w, y: -h},
        {x: 0, y: -h},
    ];
    node.intersect = function(point) {
        return dagreD3.intersect.polygon(node, points, point);
    }
    return parent;
}
// Render will link the graph back to the guts of the SVG file.
render(inner, graph);

var initialScale = 0.75;
svg.call(zoom.transform, d3.zoomIdentity.translate((svg.attr("width") - graph.graph().width * initialScale) / 2, 20).scale(initialScale));
svg.attr('height', graph.graph().height * initialScale + 40);