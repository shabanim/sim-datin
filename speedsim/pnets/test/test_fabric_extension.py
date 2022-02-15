import os
import unittest

import pandas
from pandas.testing import assert_frame_equal

from pnets.attributes import PROCESSING, READ, WRITE
from pnets.custom.extensions import SimpleFabricExtension
from pnets.pn_model import PnmlModel
from pnets.simulation import Simulator
from pnets.utils.utils import flat_model_to_rpw


class HW:
    """
    HW resources names
    """
    CPU = "CPU"
    CPU_DMA0 = "CPU.DMA0"
    CPU_PROC = "CPU.PROC"
    GT_MEDIA = "GT_MEDIA"
    GT_GFX = "GT_GFX"
    GT_DMA0 = "GT.DMA0"
    GT_DMA1 = "GT.DMA1"
    GT_GFX_PROC = "GT_GFX.PROC"
    GT_MEDIA_PROC = "GT_MEDIA.PROC"
    DISPLAY = "DISPLAY"
    DISPLAY_DMA0 = "DISPLAY.DMA0"
    DISPLAY_PROC = "DISPLAY.PROC"
    OPTIMAL_BW = 6400  # Bytes/us
    CYCLE = 0.01  # us


# Conversion function from data to run time
def data_to_runtime(data):
    return data/HW.OPTIMAL_BW


class TestCustomFabricExtension(unittest.TestCase):
    def test_simple_fabric_extension(self):
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
        Tests simple fabric model changes system bw according to parallel read/write tasks count
        """
        net = PnmlModel.Net(
            transitions=[
                PnmlModel.Transition("task1", id="task1", runtime=100.0, memory="20", read_percentage="50",
                                     hw_resource=HW.CPU),
                PnmlModel.Transition("task2", id="task2", runtime=130.0, memory="20", read_percentage="50",
                                     hw_resource=HW.CPU),
                PnmlModel.Transition("task3", id="task3", runtime=200.0, memory="20", read_percentage="50",
                                     hw_resource=HW.GT_MEDIA),
                PnmlModel.Transition("task4", id="task4", runtime=15, memory="20", read_percentage="50",
                                     hw_resource=HW.GT_GFX)
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

        resources_dict = {
            (HW.CPU, READ): HW.CPU_DMA0,
            (HW.CPU, PROCESSING): HW.CPU_PROC,
            (HW.CPU, WRITE): HW.CPU_DMA0,
            (HW.GT_GFX, READ): HW.GT_DMA0,
            (HW.GT_GFX, PROCESSING): HW.GT_GFX_PROC,
            (HW.GT_GFX, WRITE): HW.GT_DMA0,
            (HW.GT_MEDIA, READ): HW.GT_DMA1,
            (HW.GT_MEDIA, PROCESSING): HW.GT_MEDIA_PROC,
            (HW.GT_MEDIA, WRITE): HW.GT_DMA1,
            (HW.DISPLAY, READ): HW.DISPLAY_DMA0,
            (HW.DISPLAY, PROCESSING): HW.DISPLAY_PROC,
            (HW.DISPLAY, WRITE): HW.DISPLAY_DMA0
        }

        # Flattening PNML Model - each task to read -> proc -> write task
        model = flat_model_to_rpw(model, data_to_runtime, resources_dict)
        sim = Simulator(model, resources={
            HW.CPU_DMA0: 1,
            HW.CPU_PROC: 1,
            HW.GT_DMA0: 1,
            HW.GT_GFX_PROC: 1,
            HW.GT_DMA1: 1,
            HW.GT_MEDIA_PROC: 1,
            HW.DISPLAY_DMA0: 1,
            HW.DISPLAY_PROC: 1,
        })

        ex = SimpleFabricExtension(sim, HW.OPTIMAL_BW)  # noqa
        events = sim.run(15000)
        path = os.path.dirname(os.path.realpath(__file__))
        expected = pandas.read_csv(path + '/golden/simple_fabric.csv')
        assert_frame_equal(events, expected)
