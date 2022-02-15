.. toctree::
   :maxdepth: 2
   :caption: Contents:

Introduction
============
*pnets* is a python module for manipulating Petri-Nets - an abstract process representation http://www.pnml.org/.
It provides API to define, read and write Petri-Net instances (through :class:`~pnets.pn_model.PnmlModel`) and a simple simulation engine.

Example:

.. code-block:: python

   from pnets import PnmlModel
   """
        Below code creates the following PNML model:
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

    model = PnmlModel(nets=[
        PnmlModel.Net(places=places, transitions=transitions, arcs=arcs)
    ])


Classes
=======
.. autosummary::
   pnets.PnmlModel
   pnets.pn_model.PnmlModel.Net
   pnets.PnmlModel.Transition
   pnets.PnmlModel.Place
   pnets.simulation.Simulator

Functions
=========
.. autosummary::
   pnets.simulation.simulate_model

Details
=======
.. automodule:: pnets
    :members:
    :no-undoc-members:

.. automodule:: pnets.simulation
    :members:
    :no-undoc-members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
