###################################################################################
# Infra for Multi-Dispatch BEGIN
# Should put this in a separate file/module
###################################################################################
import itertools
from .network import Network
from .collective import Collective


def allsubclasses(cls):
    subclasses = cls.__subclasses__()
    for subclass in subclasses:
        subclasses.extend(allsubclasses(subclass))
    return subclasses


class _MultiMethod:
    def __init__(self, name):
        self.name = name
        self.typemap = {}

    def __call__(self, *args):
        # use only 2 args for type awarenes
        types = tuple(arg.__class__ for arg in args[:2])
        try:
            return self.typemap[types](*args)
        except KeyError:
            raise TypeError('no match %s for types %s' % (self.name, types))

    def register_function_for_types(self, types, function):
        types_with_subclasses = []
        for ty in types:
            types_with_subclasses.append([ty] + allsubclasses(ty))
        for type_tuple in itertools.product(*types_with_subclasses):
            self.typemap[type_tuple] = function


_multi_registry = {}


def multimethod(*types):
    def register(function):
        name = function.__name__
        mm = _multi_registry.get(name)
        if mm is None:
            mm = _multi_registry[name] = _MultiMethod(name)
        mm.register_function_for_types(types, function)
        return mm

    return register


# Base case: Important to Register This First
@multimethod(Network, Collective)
def comms(network, collective, message_size, tiles_per_socket, sockets):
    raise Exception("not implemented network {} collective {}"
                    .format(network, collective))

###################################################################################
# Infra for Multi-Dispatch END
###################################################################################
