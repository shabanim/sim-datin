def pnml_compare(m1, m2, attributes=None):
    """
    Compare two PNML models. Used in unit testing.
    Compares number of nodes and sum of a subset of attributes.

    :param m1: PnmlModel #1 to compare
    :param m2: PnmlModel #2 to compare
    :param attributes: list of transition attributes to compare (totals)
    :return: True if successfull, otherwise an exception is raised
    """
    num_nets = (len(m1.nets), len(m2.nets))
    if num_nets[0] != num_nets[1]:
        raise Exception("Number of nets is different: {} vs {}".format(num_nets[0], num_nets[1]))

    num_tran = (
        len([t for net in m1.nets for t in net.transitions]),
        len([t for net in m2.nets for t in net.transitions])
    )
    if num_tran[0] != num_tran[1]:
        raise Exception("Number of transitions is different: {} vs {}".format(num_tran[0], num_tran[1]))

    num_places = (
        len([t for net in m1.nets for t in net.places]),
        len([t for net in m2.nets for t in net.places])
    )
    if num_places[0] != num_places[1]:
        raise Exception("Number of places is different: {} vs {}".format(num_places[0], num_places[1]))

    # verify requested attributes:
    for attr in (attributes or tuple()):
        values = (
            sum([t.get_attribute(attr, default=0) for net in m1.nets for t in net.transitions]),
            sum([t.get_attribute(attr, default=0) for net in m2.nets for t in net.transitions])
        )
        print('-D- Comparing', attr, ':', *values)
        if values[0] != values[1] and abs(values[0] - values[1]) / (abs(values[0]) + abs(values[1])) > 1e-3:
            raise Exception("Attribute values mismatch for {}: {} vs {}".format(attr, values[0], values[1]))

    return True
