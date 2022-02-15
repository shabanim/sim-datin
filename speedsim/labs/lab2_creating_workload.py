"""
Lab2 - Creating workload, demonstrates all workload building steps including removing connections and so.
"""
from asap.workload import TYPES, Task, Workload


def create_workload():
    workload = Workload('Workload')

    # Tasks creation
    start = Task('Start', TYPES.START)
    task1 = Task('Task1', TYPES.PROC, processing_cycles=1000)
    task2 = Task('Task2', TYPES.PROC, processing_cycles=1000)
    task3 = Task('Task3', TYPES.PROC, processing_cycles=1000)

    workload.add_tasks([start, task1, task2, task3])
    end = Task('end', TYPES.END)
    workload.add_task(end)

    workload.connect_tasks('con1', start, task1)
    workload.connect_tasks('con2', start, task2)
    workload.connect_tasks('con3', start, task3)
    workload.connect_tasks('con4', task1, end)
    workload.connect_tasks('con5', task2, end)
    workload.connect_tasks('con6', task3, end)

    task4 = Task('Task4', TYPES.PROC, processing_cycles=2200)
    task5 = Task('Task5', TYPES.PROC, processing_cycles=800)

    workload.add_tasks([task4, task5])
    workload.disconnect_tasks(task1, end)
    workload.disconnect_tasks(task2, end)
    workload.del_connection('con6')

    workload.connect_tasks('con7', task2, task4)
    workload.connect_tasks('con8', task3, task4)
    workload.connect_tasks('con9', task4, task5)
    workload.connect_tasks('con10', task1, task5)
    workload.connect_tasks('con11', task5, end)

    return workload
