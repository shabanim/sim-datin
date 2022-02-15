from collections import OrderedDict
#from constants import Constants


class Collective(OrderedDict):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "Collective Constructor Check Fail!!"
        super(Collective, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True

    def __str__(self):
        return self.__class__.__name__


class AllReduce(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "Allreduce Constructor Check Fail!!"
        super(AllReduce, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Gather(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "Gather Constructor Check Fail!!"
        super(Gather, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Scatter(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "Scatter Constructor Check Fail!!"
        super(Scatter, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True

class ReduceScatter(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "ReduceScatter Constructor Check Fail!!"
        super(ReduceScatter, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class AllGather(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "AllGather Constructor Check Fail!!"
        super(AllGather, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class All2All(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "All2All Constructor Check Fail!!"
        super(All2All, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Reduce(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "Reduce Constructor Check Fail!!"
        super(Reduce, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True


class Broadcast(Collective):
    def __init__(self, knobs):
        assert self.check_knobs(knobs), "Broadcast Constructor Check Fail!!"
        super(Broadcast, self).__init__(knobs)

    def check_knobs(self, knobs):
        return True

