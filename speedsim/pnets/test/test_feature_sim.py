from unittest import TestCase

import pandas.testing

from pnets import PnmlModel
from pnets import attributes as PnAttr
from pnets.features import FeatureDesc, simulate_feature_graph

# from pnets.io import sim_results_to_event_trace
# import json


class TestFeatureSim(TestCase):
    def test_feature_sim(self):
        """
            Simple simulation with features.
            One feature:

                        //-> [f1] -\\
                [start]            [f3] -> [end]
                        \\ -> [f2] -//

                resources: r1=[f1, f3], r2=[f2]

            Top level:

               [start] -> [t1, feature: f1] -> [t2: feature: f1] -> [end]
        """
        top_model = PnmlModel(nets=[
            PnmlModel.Net(
                places=[
                    PnmlModel.Place("start", id="start", type=PnmlModel.Place.Type.START),
                    PnmlModel.Place("buff", id="buff", type=PnmlModel.Place.Type.BUFFER, **{PnAttr.BUFFER_SIZE: 1}),
                    PnmlModel.Place("end", id="end", type=PnmlModel.Place.Type.END)
                ],
                transitions=[
                    PnmlModel.Transition("t1", id="t1", **{PnAttr.FEATURE: 'f', PnAttr.HW_RESOURCE: 'r'}),
                    PnmlModel.Transition("t2", id="t2", **{PnAttr.FEATURE: 'f', PnAttr.HW_RESOURCE: 'r'})
                ],
                arcs=[
                    PnmlModel.Arc("start", "t1", **{PnAttr.WEIGHT: 1}),
                    PnmlModel.Arc("t1", "buff", **{PnAttr.WEIGHT: 1}),
                    PnmlModel.Arc("buff", "t2", **{PnAttr.WEIGHT: 1}),
                    PnmlModel.Arc("t2", "end", **{PnAttr.WEIGHT: 1})
                ]
            )
        ])

        features = {
            'f': FeatureDesc(PnmlModel(nets=[
                PnmlModel.Net(
                    places=[
                        PnmlModel.Place("start1", id="start1", type=PnmlModel.Place.Type.START),
                        PnmlModel.Place("start2", id="start2", type=PnmlModel.Place.Type.START),
                        PnmlModel.Place("b1", id="b1", type=PnmlModel.Place.Type.BUFFER, **{PnAttr.BUFFER_SIZE: 1}),
                        PnmlModel.Place("b2", id="b2", type=PnmlModel.Place.Type.BUFFER, **{PnAttr.BUFFER_SIZE: 1}),
                        PnmlModel.Place("end", id="end", type=PnmlModel.Place.Type.END)
                    ],
                    transitions=[
                        PnmlModel.Transition("f1", id="f1", **{PnAttr.HW_RESOURCE: 'r1', PnAttr.RUNTIME: 1.0}),
                        PnmlModel.Transition("f2", id="f2", **{PnAttr.HW_RESOURCE: 'r2', PnAttr.RUNTIME: 2.0}),
                        PnmlModel.Transition("f3", id="f3", **{PnAttr.HW_RESOURCE: 'r1', PnAttr.RUNTIME: 3.0})
                    ],
                    arcs=[
                        PnmlModel.Arc("start1", "f1", **{PnAttr.WEIGHT: 1}),
                        PnmlModel.Arc("start2", "f2", **{PnAttr.WEIGHT: 1}),
                        PnmlModel.Arc("f1", "b1", **{PnAttr.WEIGHT: 1}),
                        PnmlModel.Arc("f2", "b2", **{PnAttr.WEIGHT: 1}),
                        PnmlModel.Arc("b1", "f3", **{PnAttr.WEIGHT: 1}),
                        PnmlModel.Arc("b2", "f3", **{PnAttr.WEIGHT: 1}),
                        PnmlModel.Arc("f3", "end", **{PnAttr.WEIGHT: 1})
                    ]
                )
            ]), {'r1': 1, 'r2': 1})
        }

        res = simulate_feature_graph(top_model, {'r': 1}, features)

        expected = pandas.DataFrame([
            (0.0, 1.0, 't1.f1', 'r.r1', 0, 1.0),
            (0.0, 2.0, 't1.f2', 'r.r2', 0, 2),
            (0.0, 5, 't1', 'r', 0, 5),
            (2.0, 5, 't1.f3', 'r.r1', 0, 3),
            (5.0, 6, 't2.f1', 'r.r1', 0, 1),
            (5.0, 7, 't2.f2', 'r.r2', 0, 2),
            (5.0, 10, 't2', 'r', 0, 5),
            (7.0, 10, 't2.f3', 'r.r1', 0, 3)
        ], columns=['START', 'FINISH', 'TRANSITION', 'RESOURCE', 'RESOURCE_IDX', 'DURATION'])

        pandas.testing.assert_frame_equal(res, expected)

        # debug output in TraceEvent format
        # event_trace = sim_results_to_event_trace(res)
        # with open('C:/Users/gshklove/work/tmp/trace.json', 'w') as stream:
        #    json.dump(event_trace, stream, indent=True)
