import unittest

import pandas
from pandas.testing import assert_frame_equal

from pnets.pn_model import HW_RESOURCE, PnmlModel
from pnets.simulation import EVENTS, NAN, Simulator

# from _speed.trace2pred.task_graph import TaskGraph


class TestPnSim(unittest.TestCase):
    def test_pn_sim1(self):
        """
        Simple test with the following PN model:
                      (start)
                         |
                    [cpu_task1]
                      /    \
                    (1)    (1)
                    /        \
              [gpu_task1]  [cpu_task2]
                   \\         //
                   (1)      (1)
                     \\     //
                     [cpu_task3]
                         |
                       (end)
        """
        transitions = [
            PnmlModel.Transition("cpu_task1", id="cpu_task1", runtime=1, hw_resource=HW_RESOURCE.CPU.value),
            PnmlModel.Transition("gpu_task1", id="gpu_task1", runtime=2, hw_resource=HW_RESOURCE.GT_GFX.value),
            PnmlModel.Transition("cpu_task2", id="cpu_task2", runtime=.5, hw_resource=HW_RESOURCE.CPU.value),
            PnmlModel.Transition("cpu_task3", id="cpu_task3", runtime=1.5, hw_resource=HW_RESOURCE.CPU.value)
        ]
        places = [
            PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task1->gpu_task1", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task1->cpu_task2", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="gpu_task1->cpu_task3", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task2->cpu_task3", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end")
        ]
        arcs = [
            PnmlModel.Arc("start", "cpu_task1", "", weight=1),

            PnmlModel.Arc("cpu_task1", "cpu_task1->gpu_task1", "", weight=1),
            PnmlModel.Arc("cpu_task1->gpu_task1", "gpu_task1", "", weight=1),

            PnmlModel.Arc("cpu_task1", "cpu_task1->cpu_task2", "", weight=1),
            PnmlModel.Arc("cpu_task1->cpu_task2", "cpu_task2", "", weight=1),

            PnmlModel.Arc("gpu_task1", "gpu_task1->cpu_task3", "", weight=1),
            PnmlModel.Arc("gpu_task1->cpu_task3", "cpu_task3", "", weight=1),

            PnmlModel.Arc("cpu_task2", "cpu_task2->cpu_task3", "", weight=1),
            PnmlModel.Arc("cpu_task2->cpu_task3", "cpu_task3", "", weight=1),

            PnmlModel.Arc("cpu_task3", "end", "", weight=1),
        ]

        net = PnmlModel.Net(places=places, transitions=transitions, arcs=arcs)
        model = PnmlModel(nets=[net])

        sim = Simulator(model, resources={
            HW_RESOURCE.CPU.value: 2,
            HW_RESOURCE.GT_GFX.value: 1
        })

        # test tick events:
        ticks = []

        def _on_tick():
            ticks.append(sim.now)

        sim.connect_to_event(EVENTS.CLOCK_TICK, _on_tick)

        expected = pandas.DataFrame(data=[
            (0, 1, 'cpu_task1', 'CPU', 0, 1),
            (1, 1.5, 'cpu_task2', 'CPU', 0, 0.5),
            (1, 3, 'gpu_task1', 'GT_GFX', 0, 2),
            (3, 4.5, 'cpu_task3', 'CPU', 0, 1.5),

        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.run(10)

        assert_frame_equal(events, expected)
        self.assertListEqual(ticks, [0.0, 1.0, 1.5, 3, 4.5])  # tick "1.0" should be reported only once
        self.assertListEqual(model.playback(), ['cpu_task1', 'gpu_task1', 'cpu_task2', 'cpu_task3'])

    def test_pn_loop_sim(self):
        """
        Test simulating PN with loops.
                    (start)
                       |
                    [task1]
                       |
                      (3)
                       |  /--\\
                    [task2]  (1)
                       |  \\__/
                      (3)
                       |
                    [task3]
                       |
                     (end)
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=1.0, hw_resource=HW_RESOURCE.CPU.value),
                PnmlModel.Transition("task2", id="task2", runtime=1.0, hw_resource=HW_RESOURCE.CPU.value),
                PnmlModel.Transition("task3", id="task3", runtime=1.0, hw_resource=HW_RESOURCE.CPU.value),
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p1", init_count=0, buff_size=3),  # loop enter
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p2", init_count=0, buff_size=3),  # loop exit
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p3", init_count=1, buff_size=1),  # loop back
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
            ],
            arcs=[
                PnmlModel.Arc("start", "task1", "", weight=1),

                PnmlModel.Arc("task1", "p1", "", weight=3),
                PnmlModel.Arc("p1", "task2", "", weight=1),

                PnmlModel.Arc("task2", "p2", "", weight=1),
                PnmlModel.Arc("p2", "task3", "", weight=3),

                PnmlModel.Arc("task2", "p3", "", weight=1),
                PnmlModel.Arc("p3", "task2", "", weight=1),

                PnmlModel.Arc("task3", "end", "", weight=1),
            ]
        )

        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            HW_RESOURCE.CPU.value: 1
        })

        expected = pandas.DataFrame(data=[
            (0.0, 1.0, 'task1', 'CPU', 0, 1.0),
            (1.0, 2.0, 'task2', 'CPU', 0, 1.0),
            (2.0, 3.0, 'task2', 'CPU', 0, 1.0),
            (3.0, 4.0, 'task2', 'CPU', 0, 1.0),
            (4.0, 5.0, 'task3', 'CPU', 0, 1.0)

        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.run(10)
        assert_frame_equal(events, expected)
        self.assertListEqual(model.playback(), ['task1', 'task2', 'task2', 'task2', 'task3'])

    def test_pn_delays_sim(self):
        """
        Test simulation with start delays and repeat frequency
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=2, hw_resource=HW_RESOURCE.CPU.value),
                PnmlModel.Transition("task2", id="task2", runtime=2, hw_resource=HW_RESOURCE.CPU.value),
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start1", start_delay=0),
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start2", start_delay=1, frequency=1/4e-6),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
            ],
            arcs=[
                PnmlModel.Arc("start1", "task1", "", weight=1),
                PnmlModel.Arc("task1", "end", "", weight=1),

                PnmlModel.Arc("start2", "task2", "", weight=1),
                PnmlModel.Arc("task2", "end", "", weight=1),
            ]
        )

        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            HW_RESOURCE.CPU.value: 2
        })

        expected = pandas.DataFrame(data=[
            (0.0, 2.0, 'task1', 'CPU', 0, 2),
            (1.0, 3.0, 'task2', 'CPU', 1, 2),
            (5.0, 7.0, 'task2', 'CPU', 0, 2.0),
            (9.0, NAN, 'task2', 'CPU', 0, NAN),
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.run(10)
        assert_frame_equal(events, expected)

    def test_pn_multi_sim(self):
        """
        Test simulating 1 to N ratios.
        t1 -3-> (3) -1-> t2
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition('t1', id='t1', runtime=1.0, hw_resource=HW_RESOURCE.CPU.value),
                PnmlModel.Transition('t2', id='t2', runtime=1.0, hw_resource=HW_RESOURCE.CPU.value)
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p1", buff_size=3),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
            ],
            arcs=[
                PnmlModel.Arc("start", "t1", "", weight=1),
                PnmlModel.Arc("t1", "p1", "", weight=3),
                PnmlModel.Arc("p1", "t2", "", weight=1),
                PnmlModel.Arc("t2", "end", "", weight=1),
            ]
        )

        expected = pandas.DataFrame(data=[
            (0.0, 1.0, 't1', 'CPU', 0, 1.0),
            (1.0, 2.0, 't2', 'CPU', 0, 1.0),
            (2.0, 3.0, 't2', 'CPU', 0, 1.0),
            (3.0, 4.0, 't2', 'CPU', 0, 1.0),
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            HW_RESOURCE.CPU.value: 1
        })

        events = sim.run(10)
        assert_frame_equal(events, expected)

    def test_null_resource(self):
        """
        Test simulation with task2 mapped to NULL resource (no resource property)
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=1.0, hw_resource=HW_RESOURCE.CPU.value),
                PnmlModel.Transition("task2", id="task2", runtime=1.0),
                PnmlModel.Transition("task3", id="task3", runtime=1.0, hw_resource=HW_RESOURCE.CPU.value),
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p1", buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p2", buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
            ],
            arcs=[
                PnmlModel.Arc("start", "task1", "", weight=1),
                PnmlModel.Arc("task1", "p1", "", weight=1),
                PnmlModel.Arc("p1", "task2", "", weight=1),
                PnmlModel.Arc("task2", "p2", "", weight=1),
                PnmlModel.Arc("p2", "task3", "", weight=1),
                PnmlModel.Arc("task3", "end", "", weight=1),
            ]
        )
        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            HW_RESOURCE.CPU.value: 1
        })

        expected = pandas.DataFrame(data=[
            (0.0, 1.0, 'task1', 'CPU', 0, 1.0),
            (1.0, 2.0, 'task2', 'NULL', 0, 1.0),
            (2.0, 3.0, 'task3', 'CPU', 0, 1.0,)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.run(10)
        assert_frame_equal(events, expected)

    def test_multiple_resource(self):
        """
        Test simulation with multiple resources available for a task
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=1.0, hw_resource=','.join(['A', 'B'])),
                PnmlModel.Transition("task2", id="task2", runtime=1.5, hw_resource=','.join(['B', 'A']))
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start1"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end1"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start2"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end2"),
            ],
            arcs=[
                PnmlModel.Arc("start1", "task1", "", weight=1),
                PnmlModel.Arc("start2", "task2", "", weight=1),
                PnmlModel.Arc("task1", "end1", "", weight=1),
                PnmlModel.Arc("task2", "end2", "", weight=1),
            ]
        )
        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            'A': 1,
            'B': 1
        })

        expected = pandas.DataFrame(data=[
            (0, 1.0, 'task1', 'A', 0, 1.0),
            (0, 1.5, 'task2', 'B', 0, 1.5),
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.run(10)
        assert_frame_equal(events, expected)

    def test_multiple_tokens(self):
        """
        Test 1-to-N N-to-1 token propagation
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", hw_resource='A'),
                PnmlModel.Transition("task2", id="task2", hw_resource='A'),
                PnmlModel.Transition("task3", id="task3", hw_resource='A'),
                PnmlModel.Transition("task4", id="task4", hw_resource='A'),
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p1", init_count=0, buff_size=3),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p2", init_count=0, buff_size=3),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p3", init_count=0, buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="p4", init_count=0, buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
            ],
            arcs=[
                PnmlModel.Arc("start", "task1", "", weight=1),

                PnmlModel.Arc("task1", "p1", "", weight=3),
                PnmlModel.Arc("p1", "task2", "", weight=1),

                PnmlModel.Arc("task2", "p2", "", weight=1),
                PnmlModel.Arc("p2", "task4", "", weight=3),

                PnmlModel.Arc("task1", "p3", "", weight=1),
                PnmlModel.Arc("p3", "task3", "", weight=1),

                PnmlModel.Arc("task3", "p4", "", weight=1),
                PnmlModel.Arc("p4", "task4", "", weight=1),

                PnmlModel.Arc("task4", "end", "", weight=1),
            ]
        )

        model = PnmlModel(nets=[net])
        self.assertListEqual(model.playback(), ['task1', 'task2', 'task2', 'task2', 'task3', 'task4'])

    def test_priority(self):
        """
        Simple test with the following PN model:
                (start)
                   |
                  __[task1]___
                 /    \\      \\
               (1)    (1)     (1)
               /       \\       \\
             [task3]  [task2]  [task4]
              \\        \\       \\
              \\        \\      [task5]
               \\       \\        /
               (1)     (1)     (1)
                 \\     /      /
                  \\__(end)___/
        All tasks are mapped to same ip but with different priorities
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=1.0, hw_resource="Core"),
                PnmlModel.Transition("task2", id="task2", runtime=3.0, hw_resource="Core", priority=1),
                PnmlModel.Transition("task3", id="task3", runtime=10.0, hw_resource="Core", priority=10),
                PnmlModel.Transition("task4", id="task4", runtime=5, hw_resource="Core", priority=5),
                PnmlModel.Transition("task5", id="task5", runtime=5, hw_resource="Core", priority=5)
            ],
            places=[
                PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end"),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b1", init=0, buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b2", init=0, buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b3", init=0, buff_size=1),
                PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="b4", init=0, buff_size=1),
            ],
            arcs=[
                PnmlModel.Arc("start", "task1", "", weight=1),
                PnmlModel.Arc("task1", "b1", "", weight=1),
                PnmlModel.Arc("task1", "b2", "", weight=1),
                PnmlModel.Arc("task1", "b3", "", weight=1),
                PnmlModel.Arc("b1", "task2", "", weight=1),
                PnmlModel.Arc("b2", "task3", "", weight=1),
                PnmlModel.Arc("b3", "task4", "", weight=1),
                PnmlModel.Arc("task4", "b4", "", weight=1),
                PnmlModel.Arc("b4", "task5", "", weight=1),
                PnmlModel.Arc("task2", "end", "", weight=1),
                PnmlModel.Arc("task3", "end", "", weight=1),
                PnmlModel.Arc("task5", "end", "", weight=1),
            ]
        )
        model = PnmlModel(nets=[net])
        sim = Simulator(model, resources={
            "Core": 1
        })

        events = sim.run(30)
        expected = pandas.DataFrame(data=[
            (0.0, 1.0,  "task1", "Core", 0, 1.0),
            (1.0, 11.0,  "task3", "Core", 0, 10.0),
            (11.0, 16.0, "task4", "Core", 0, 5.0),
            (16.0, 21.0, "task5", "Core", 0, 5.0),
            (21.0, 24.0,  "task2", "Core", 0, 3.0)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        assert_frame_equal(events, expected)

    def test_pn_token_consumption(self):
        """
        Simple test with the following PN model:
                      (start)
                         |
                      [task1]
                         | w=3
                        (10)
                         | w=1
                      [task2]
                         |
                        (1)
                         |
                      [task3]
                         | w=1
                        (10)
                         | w=3
                      [task4]
                         |
                       (end)
        Check that token consumption and tasks executing done correctly
        """
        transitions = [
            PnmlModel.Transition("task1", id="task1", runtime=1, hw_resource=HW_RESOURCE.CPU.value),
            PnmlModel.Transition("task2", id="task2", runtime=1, hw_resource=HW_RESOURCE.CPU.value),
            PnmlModel.Transition("task3", id="task3", runtime=1.5, hw_resource=HW_RESOURCE.CPU.value),
            PnmlModel.Transition("task4", id="task4", runtime=2, hw_resource=HW_RESOURCE.CPU.value)
        ]
        places = [
            PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="task1->task2", init=0, buff_size=10),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="task2->task3", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="task3->task4", init=0, buff_size=10),
            PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end")
        ]
        arcs = [
            PnmlModel.Arc("start", "task1", "", weight=1),
            PnmlModel.Arc("task1", "task1->task2", "", weight=3),
            PnmlModel.Arc("task1->task2", "task2", "", weight=1),
            PnmlModel.Arc("task2", "task2->task3", "", weight=1),
            PnmlModel.Arc("task2->task3", "task3", "", weight=1),
            PnmlModel.Arc("task3", "task3->task4", "", weight=1),
            PnmlModel.Arc("task3->task4", "task4", "", weight=3),
            PnmlModel.Arc("task4", "end", "", weight=1),
        ]

        net = PnmlModel.Net(places=places, transitions=transitions, arcs=arcs)
        model = PnmlModel(nets=[net])

        sim = Simulator(model, resources={
            HW_RESOURCE.CPU.value: 1
        })

        expected = pandas.DataFrame(data=[
            (0, 1, 'task1', 'CPU', 0, 1),
            (1, 2, 'task2', 'CPU', 0, 1),
            (2, 3.5, 'task3', 'CPU', 0, 1.5),
            (3.5, 4.5, 'task2', 'CPU', 0, 1),
            (4.5, 6, 'task3', 'CPU', 0, 1.5),
            (6, 7, 'task2', 'CPU', 0, 1),
            (7, 8.5, 'task3', 'CPU', 0, 1.5),
            (8.5, 10.5, 'task4', 'CPU', 0, 2),

        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        events = sim.run(12)
        assert_frame_equal(events, expected)
