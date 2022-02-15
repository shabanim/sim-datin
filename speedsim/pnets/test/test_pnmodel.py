import io
from unittest import TestCase

from pnets import PnmlModel


class TestPnModel(TestCase):
    def test_dag(self):
        """
        Test converting PNModel to DAG
                      (start)
                         |
                    [cpu_task1]
                      /    \
                    (1)    (3)
                    /        \
              [gpu_task1]  [cpu_task2]
                   \\         //
                   (1)      (3)
                     \\     //
                     [cpu_task3]
                         |
                       (end)
        """
        transitions = [
            PnmlModel.Transition("cpu_task1", id="cpu_task1"),
            PnmlModel.Transition("gpu_task1", id="gpu_task1"),
            PnmlModel.Transition("cpu_task2", id="cpu_task2"),
            PnmlModel.Transition("cpu_task3", id="cpu_task3")
        ]
        places = [
            PnmlModel.Place('', type=PnmlModel.Place.Type.START, id="start"),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task1->gpu_task1", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task1->cpu_task2", init=0, buff_size=3),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="gpu_task1->cpu_task3", init=0, buff_size=1),
            PnmlModel.Place('', type=PnmlModel.Place.Type.BUFFER, id="cpu_task2->cpu_task3", init=0, buff_size=3),
            PnmlModel.Place('', type=PnmlModel.Place.Type.END, id="end")
        ]
        arcs = [
            PnmlModel.Arc("start", "cpu_task1", "", weight=1),

            PnmlModel.Arc("cpu_task1", "cpu_task1->gpu_task1", "", weight=1),
            PnmlModel.Arc("cpu_task1->gpu_task1", "gpu_task1", "", weight=1),

            PnmlModel.Arc("cpu_task1", "cpu_task1->cpu_task2", "", weight=3),
            PnmlModel.Arc("cpu_task1->cpu_task2", "cpu_task2", "", weight=1),

            PnmlModel.Arc("gpu_task1", "gpu_task1->cpu_task3", "", weight=1),
            PnmlModel.Arc("gpu_task1->cpu_task3", "cpu_task3", "", weight=1),

            PnmlModel.Arc("cpu_task2", "cpu_task2->cpu_task3", "", weight=1),
            PnmlModel.Arc("cpu_task2->cpu_task3", "cpu_task3", "", weight=3),

            PnmlModel.Arc("cpu_task3", "end", "", weight=1),
        ]

        net = PnmlModel.Net(places=places, transitions=transitions, arcs=arcs)
        model = PnmlModel(nets=[net])

        dag = model.to_dag()
        self.assertSetEqual(set(dag.nodes), {
            ('cpu_task1', 0),
            ('cpu_task2', 0),
            ('cpu_task2', 1),
            ('cpu_task2', 2),
            ('gpu_task1', 0),
            ('cpu_task3', 0)
        })

        self.assertSetEqual(set(dag.edges), {
            (('cpu_task1', 0), ('cpu_task2', 0)),
            (('cpu_task1', 0), ('cpu_task2', 1)),
            (('cpu_task1', 0), ('cpu_task2', 2)),

            (('cpu_task2', 0), ('cpu_task2', 1)),
            (('cpu_task2', 1), ('cpu_task2', 2)),
            (('cpu_task2', 2), ('cpu_task3', 0)),

            (('cpu_task1', 0), ('gpu_task1', 0)),
            (('gpu_task1', 0), ('cpu_task3', 0)),
        })

    def test_persistency(self):
        """
        Test persistency for generic JSON attributes
        """
        model = PnmlModel()

        expected_val = {
            "test1": "reku",
            "test2": 10,
            "test3": 11.1
        }

        expected_val_test6 = [{'a': 1, 'b': 'abc', 'c': 2.0}, {'a2': 12, 'b2': 'abc2', 'c2': 22.0}]

        model.set_attribute("testme", expected_val)
        model.set_attribute("testme2", "Test Me 2")
        model.set_attribute("testme3", 10)
        model.set_attribute("testme4", 11.0)
        model.set_attribute("testme5", ["a", 10, 12.0])
        model.set_attribute("testme6", expected_val_test6)

        stream = io.BytesIO()
        model.save(stream)
        xml = stream.getvalue()

        stream = io.BytesIO(xml)
        model = PnmlModel.read(stream)

        self.assertDictEqual(expected_val, model.get_attribute("testme"))
        self.assertEqual("Test Me 2", model.get_attribute("testme2"))
        self.assertEqual(10, model.get_attribute("testme3"))
        self.assertEqual(11.0, model.get_attribute("testme4"))
        self.assertListEqual(["a", 10, 12.0], model.get_attribute("testme5"))
        self.assertListEqual(expected_val_test6, model.get_attribute("testme6"))
