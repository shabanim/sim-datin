import unittest

import pandas
from pandas.testing import assert_frame_equal

from pnets.custom.extensions import ComplexLoadExtension, LoadExtension
from pnets.pn_model import PnmlModel
from pnets.simulation import Simulator

BIG_CORE = "Big_Core"


class Model:
    """
    Simple test with the following PN model:
                (start)
                   |
              __[task1]___
             /    \\      \\
           (1)    (1)     (1)
           /        \\      \\
         [task3]  [task2]  [task4]
           \\        /      /
           (1)     (1)    (1)
             \\     /      /
              \\__(end)___/
    All tasks are mapped to Big Core
    """
    net = PnmlModel.Net(
        transitions=[
            PnmlModel.Transition("task1", id="task1", runtime=1.0, hw_resource=BIG_CORE),
            PnmlModel.Transition("task2", id="task2", runtime=3.0, hw_resource=BIG_CORE),
            PnmlModel.Transition("task3", id="task3", runtime=10.0, hw_resource=BIG_CORE),
            PnmlModel.Transition("task4", id="task4", runtime=5, hw_resource=BIG_CORE)
        ],
        places=[
            PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
            PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b1", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b2", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b3", init=0, buff_size=1),
        ],
        arcs=[
            PnmlModel.Arc("start", "task1", "", weight=1),
            PnmlModel.Arc("task1", "b1", "", weight=1),
            PnmlModel.Arc("task1", "b2", "", weight=1),
            PnmlModel.Arc("task1", "b3", "", weight=1),
            PnmlModel.Arc("b1", "task2", "", weight=1),
            PnmlModel.Arc("b2", "task3", "", weight=1),
            PnmlModel.Arc("b3", "task4", "", weight=1),
            PnmlModel.Arc("task2", "end", "", weight=1),
            PnmlModel.Arc("task3", "end", "", weight=1),
            PnmlModel.Arc("task4", "end", "", weight=1),
        ]
    )


class TestCustomExtension(unittest.TestCase):
    def test_load_extension_start_events(self):

        model = PnmlModel(nets=[Model.net])
        sim = Simulator(model, resources={
            BIG_CORE: 3
        })

        ex = LoadExtension(sim)  # noqa
        events = sim.run(40)
        expected = pandas.DataFrame(data=[
            (0.0, 1.00, "task1", BIG_CORE, 0, 1.00),
            (1.0, 12.25, "task2", BIG_CORE, 0, 11.25),
            (1.0, 19.75, "task4", BIG_CORE, 2, 18.75),
            (1.0, 38.50, "task3", BIG_CORE, 1, 37.50)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        assert_frame_equal(events, expected)

    def test_load_extension_start_finish_events(self):
        model = PnmlModel(nets=[Model.net])
        sim = Simulator(model, resources={
            BIG_CORE: 3
        })

        ex = ComplexLoadExtension(sim)  # noqa
        events = sim.run(40)
        expected = pandas.DataFrame(data=[
            (0.0, 1.00, "task1", BIG_CORE, 0, 1.00),
            (1.0, 12.25, "task2", BIG_CORE, 0, 11.25),
            (1.0, 14.75, "task4", BIG_CORE, 2, 13.75),
            (1.0, 17.25, "task3", BIG_CORE, 1, 16.25)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        assert_frame_equal(events, expected)
