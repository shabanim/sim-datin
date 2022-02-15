import unittest

import pandas
from pandas.testing import assert_frame_equal

from pnets.custom.schedulers import BFScheduler, PowerScheduler
from pnets.pn_model import PnmlModel
from pnets.simulation import Simulator


class TestPnScheduler(unittest.TestCase):
    def test_custom_scheduler_simple_remap(self):
        """
        Simple test with the following PN model:
                (start)
                   |
                [task1]
                 /    \\
               (1)    (1)
               /        \\
             [task3]  [task2]
               \\        /
               (1)     (1)
                 \\    /
                  (end)
        All tasks are mapped to Big Core, if scheduler find Big Core busy then try to map to Atom
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=1.0, hw_resource=BFScheduler.BIG_CORE),
                PnmlModel.Transition("task2", id="task2", runtime=1.5, hw_resource=BFScheduler.BIG_CORE),
                PnmlModel.Transition("task3", id="task3", runtime=1.5, hw_resource=BFScheduler.BIG_CORE)
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b1", init=0, buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b2", init=0, buff_size=1),
            ],
            arcs=[
                PnmlModel.Arc("start", "task1", "", weight=1),
                PnmlModel.Arc("task1", "b1", "", weight=1),
                PnmlModel.Arc("task1", "b2", "", weight=1),
                PnmlModel.Arc("b1", "task2", "", weight=1),
                PnmlModel.Arc("b2", "task3", "", weight=1),
                PnmlModel.Arc("task2", "end", "", weight=1),
                PnmlModel.Arc("task3", "end", "", weight=1),
            ]
        )
        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            BFScheduler.BIG_CORE: 1,
            BFScheduler.ATOM: 1
        })

        sim.scheduler = BFScheduler(sim, 1.1)
        events = sim.run(10)

        expected = pandas.DataFrame(data=[
            (0.0, 1.00, "task1", BFScheduler.BIG_CORE, 0, 1.00),
            (1.0, 2.50, "task2", BFScheduler.BIG_CORE, 0, 1.50),
            (1.0, 2.65, "task3", BFScheduler.ATOM, 0, 1.65)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        assert_frame_equal(events, expected)

    def test_custom_scheduler_remap(self):
        """
        Simple test with the following PN model:
                (start)
                   |
                  __[task1]___
                 /    \\      \\
               (1)    (1)     (1)
               /       \\       \\
             [task3]  [task2]  [task4]
              \\         /      /
               (1)     (1)    (1)
                 \\     /      /
                  \\__(end)___/
        All tasks are mapped to differently, As long as scheduler sees Big Core is busy it tries to map to Atom
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=1.0, hw_resource=BFScheduler.BIG_CORE),
                PnmlModel.Transition("task2", id="task2", runtime=3.0, hw_resource=BFScheduler.ATOM),
                PnmlModel.Transition("task3", id="task3", runtime=10.0, hw_resource=BFScheduler.BIG_CORE),
                PnmlModel.Transition("task4", id="task4", runtime=5, hw_resource=BFScheduler.BIG_CORE)
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
        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            BFScheduler.BIG_CORE: 1,
            BFScheduler.ATOM: 1
        })

        sim.scheduler = BFScheduler(sim, 1.5)
        events = sim.run(30)

        expected = pandas.DataFrame(data=[
            (0.0, 1.0,  "task1", BFScheduler.BIG_CORE, 0, 1.0),
            (1.0, 5.5,  "task2", BFScheduler.ATOM, 0, 4.5),
            (1.0, 11.0, "task3", BFScheduler.BIG_CORE, 0, 10.0),
            (5.5, 13.0,  "task4", BFScheduler.ATOM, 0, 7.5)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        assert_frame_equal(events, expected)

    def test_custom_simple_power_scheduler(self):
        """
        Simple test with the following PN model:
                (start)
                   |
                [task1]
                 /    \\
               (1)    (1)
               /        \\
             [task3]  [task2]
               \\        /
               (1)     (1)
                 \\    /
                  (end)
        Different mapping, task should be delayed till the resource wake up.
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=3.0, hw_resource=BFScheduler.BIG_CORE),
                PnmlModel.Transition("task2", id="task2", runtime=4.0, hw_resource=BFScheduler.BIG_CORE),
                PnmlModel.Transition("task3", id="task3", runtime=4.0, hw_resource=BFScheduler.ATOM)
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b1", init=0, buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b2", init=0, buff_size=1),
            ],
            arcs=[
                PnmlModel.Arc("start", "task1", "", weight=1),
                PnmlModel.Arc("task1", "b1", "", weight=1),
                PnmlModel.Arc("task1", "b2", "", weight=1),
                PnmlModel.Arc("b1", "task2", "", weight=1),
                PnmlModel.Arc("b2", "task3", "", weight=1),
                PnmlModel.Arc("task2", "end", "", weight=1),
                PnmlModel.Arc("task3", "end", "", weight=1),
            ]
        )
        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            BFScheduler.BIG_CORE: 1,
            BFScheduler.ATOM: 1
        })

        sim.scheduler = PowerScheduler(sim, {BFScheduler.BIG_CORE: 2, BFScheduler.ATOM: 1})
        events = sim.run(11)

        expected = pandas.DataFrame(data=[
            (2.0, 5.00, "task1", BFScheduler.BIG_CORE, 0, 3.00),
            (5.0, 9.00, "task2", BFScheduler.BIG_CORE, 0, 4.00),
            (6.0, 10.0, "task3", BFScheduler.ATOM, 0, 4.0)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        assert_frame_equal(events, expected)
