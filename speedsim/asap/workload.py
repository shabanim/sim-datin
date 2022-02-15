"""
**Workload** definition - definition of workload and its components.
    - Task
    - Connection
"""
import os
import tempfile
from enum import Enum
from typing import List

from pnets.pn_model import PnmlModel

from .strings import NAME_SEPARATOR, TRIGGER_IN, TRIGGER_OUT, TaskMetaData


class TYPES(Enum):
    """
    Tasks types.
        - START:
        - END:
        - GEN: general task that may contain read/write data and processing cycles.
        - PROC: for processing tasks
        - READ:
        - WRITE:
        - WORKLOAD: workload tasks
    """
    START = "START"
    END = "END"
    GEN = "GENERAL"         # Task of read/process/write (or any combination)
    PROC = "PROC"           # Task only processing
    READ = "READ"           # Task only reads
    WRITE = "WRITE"         # Task only writes
    WORKLOAD = "WORKLOAD"   # Task that is workload


class Task:
    """
    Task definition class.
    Task has basic attributes which define its behavior.

    Any attribute can be attached as well. Basic attributes:
        - name
        - type
        - read_bytes
        - write bytes
        - processing cycles

    :param name: Task name
    :param type: Task type
    :param read_bytes:
    :param write_bytes:
    :param processing_cycles:
    :param kwargs:
    """
    def __init__(self, name, type=TYPES.PROC, read_bytes=0, write_bytes=0, processing_cycles=0, **kwargs):
        self._name = name
        self._type = type
        self._read_bytes = read_bytes
        self._write_bytes = write_bytes
        self._processing_cycles = processing_cycles
        self._successors = dict()
        self._predecessors = dict()
        self._counters = list()
        self._attributes = dict()
        for attribute, val in kwargs.items():
            self._attributes[attribute] = val

    @property
    def name(self):
        """
        :return: Task name
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Setting task name.

        :param name:
        :return:
        """
        self._name = name

    @property
    def type(self):
        """
        :return: Task type
        """
        return self._type

    @type.setter
    def type(self, _type):
        self._type = _type

    @property
    def read_bytes(self):
        """
        :return: Task read bytes
        """
        return self._read_bytes

    @read_bytes.setter
    def read_bytes(self, read_bytes):
        """
        Setting task read bytes.

        :param read_bytes:
        :return:
        """
        self._read_bytes = read_bytes

    @property
    def write_bytes(self):
        """
        :return: Task write bytes
        """
        return self._write_bytes

    @write_bytes.setter
    def write_bytes(self, write_bytes):
        """
        Setting task write bytes.

        :param write_bytes:
        :return:
        """
        self._write_bytes = write_bytes

    @property
    def processing_cycles(self):
        """
        :return: Task processing cycles
        """
        return self._processing_cycles

    @processing_cycles.setter
    def processing_cycles(self, processing_cycles):
        """
        Setting task processing cycles.

        :param processing_cycles:
        :return:
        """
        self._processing_cycles = processing_cycles

    @property
    def counters(self):
        """
        :return: Counters list
        """
        return self._counters

    @counters.setter
    def counters(self, counters):
        """
        Setting task counters.

        :param counters: Counters list
        :return:
        """
        self._counters = counters

    def add_counter(self, counter, override=False):
        """
        Add new counter to task counters list. If counter with the same name exists then override if override=True,
        otherwise, raise an error.

        :param counter: Counter object
        :param override: if True overrides counter with same name. Default False
        :return: raise error if override=False and counter with same name exists.
        """
        i = 0
        while i < len(self._counters):
            c = self._counters[i]
            if c.name == counter.name:
                if override:
                    self._counters.pop(i)
                else:
                    raise ValueError('Counter with the same name exists!, set override to True to override.')
            else:
                i += 1
        self._counters.append(counter)

    @property
    def predecessors(self):
        """
        Predecessors is a dictionary of task_name -> connection

        :return: predecessor tasks
        """
        return self._predecessors

    @property
    def successors(self):
        """
        Successors is a dictionary of task_name -> connection

        :return: successor tasks
        """
        return self._successors

    def connect_to_task(self, task, connection):
        """
        Connect self task to given task, override connection if already exists

        :param task: Task object to connect to
        :param connection: Connection object describes the connection between 2 tasks
        :return:
        """
        if task in self._successors:
            del self._successors[task]
        self._successors[task] = connection

    def connect_from_task(self, task, connection):
        """
        Connect given task to self, override connection if already exists

        :param task: Task object to connect from
        :param connection: Connection object describes the connection between 2 tasks
        :return:
        """
        if task in self._predecessors:
            del self._predecessors[task]
        self._predecessors[task] = connection

    def disconnect_predecessor(self, task):
        """
        Disconnecting self from given predecessor task

        :param task: Task object
        :return: True if disconnected, False otherwise or does not exist.
        """
        if task in self._predecessors:
            del self._predecessors[task]
            return True
        return False

    def disconnect_successor(self, task):
        """
        Disconnecting self from given successor task

        :param task: Task object
        :return: True if disconnected, False otherwise or does not exist.
        """
        if task in self._successors:
            del self._successors[task]
            return True
        return False

    @property
    def attributes(self):
        """
        Getting task attributes

        :return: attributes dict
        """
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes = value

    def attach_attribute(self, attribute, value):
        """
        Attaching new attribute to task with its value.

        :param attribute:
        :param value:
        :return:
        """
        self._attributes[attribute] = value

    def get_attribute(self, attribute, default=None):
        """
        Getting attribute value.

        :param attribute:
        :param default:
        :return: Attribute value, None if attribute does not exist.
        """
        return self._attributes.get(attribute, default)


class WlTask(Task):
    """
    Hierarchical task class.

    basic attributes:
        - name
        - workload
        - mapping
        - split - the number of slices to split the tasks inside the workload
    """
    def __init__(self, name, workload, mapping, split=1, **kwargs):
        self._workload = workload
        self._mapping = mapping
        self._split = split
        super().__init__(name, TYPES.WORKLOAD, 0, 0, 0, **kwargs)

    @property
    def workload(self):
        """
        :return: Workload
        """
        return self._workload

    @workload.setter
    def workload(self, workload):
        """
        Setting task internal workload.

        :param workload:
        :return:
        """
        self._workload = workload

    @property
    def mapping(self):
        """
        :return: Mapping
        """
        return self._mapping

    @mapping.setter
    def mapping(self, mapping):
        """
        Setting task internal mapping.

        :param mapping:
        :return:
        """
        self._mapping = mapping

    @property
    def split(self):
        """
        :return: Split
        """
        return self._split

    @split.setter
    def split(self, split):
        """
        Setting split value.

        :param split:
        :return:
        """
        self._split = split


class Connection:
    """
    Connection definition.
    Connections are between 2 tasks, each connection has general attributes
    which defines the behavior between source and target.

    Basic attributes:
        - source
        - target
        - init
        - put_samples
        - get_samples
        - buf_size
    """
    def __init__(self, name, source, target, init=0, put_samples=1, get_samples=1, buf_size=1, **kwargs):
        self._name = name
        self._source = source
        self._target = target
        self._init = init
        self._put_samples = put_samples
        self._get_samples = get_samples
        self._buf_size = buf_size
        self._attributes = dict()
        for attribute, val in kwargs.items():
            self._attributes[attribute] = val
        self._source.connect_to_task(self._target, self)
        self._target.connect_from_task(self._source, self)

    def __del__(self):
        if self._source and self._target:
            self._source.disconnect_successor(self._target)
            self._target.disconnect_predecessor(self._source)

    @property
    def name(self):
        """
        :return: Name
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Setting connection name.

        :param name:
        :return:
        """
        self._name = name

    @property
    def source(self):
        """
        :return: Connection source (Task)
        """
        return self._source

    @source.setter
    def source(self, source):
        """
        Setting connection source (Task).

        :param source:
        :return:
        """
        self._source = source

    @property
    def target(self):
        """
        :return: Connection target (Task).
        """
        return self._target

    @target.setter
    def target(self, target):
        """
        Setting connection target (Task).

        :param target:
        :return:
        """
        self._target = target

    @property
    def init(self):
        """
        :return: init value
        """
        return self._init

    @init.setter
    def init(self, init):
        """
        Setting init value.
        :param init:
        :return:
        """
        self._init = init

    @property
    def put_samples(self):
        """
        :return: put samples of connection
        """
        return self._put_samples

    @put_samples.setter
    def put_samples(self, put_samples):
        """
        Setting put samples.

        :param put_samples:
        :return:
        """
        self._put_samples = put_samples

    @property
    def get_samples(self):
        """
        :return: get samples of connection
        """
        return self._get_samples

    @get_samples.setter
    def get_samples(self, get_samples):
        """
        Setting get samples.

        :param get_samples:
        :return:
        """
        self._get_samples = get_samples

    @property
    def buf_size(self):
        """
        :return: Connection buffer size
        """
        return self._buf_size

    @buf_size.setter
    def buf_size(self, buf_size):
        """
        Setting connection buffer size

        :param buf_size:
        :return:
        """
        self._buf_size = buf_size

    def attach_attribute(self, attribute, value):
        """
        Attaching new attribute to the connection.

        :param attribute:
        :param value:
        :return:
        """
        self._attributes[attribute] = value

    def get_attribute(self, attribute):
        """
        Getting attribute value.

        :param attribute:
        :return: attribute value, None if does not exist.
        """
        self._attributes.get(attribute, None)


class Workload:
    """
    Workload definition.

    Consists of tasks and connections.
    """
    def __init__(self, name, tasks=None, connections: List[Connection] = None, attributes=None):
        self._name = name
        self._tasks = tasks if tasks is not None else list()
        self._connections = connections if connections is not None else list()
        self._attributes = attributes if attributes is not None else dict()

    @property
    def name(self):
        """
        :return: Workload name
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Setting workload name.

        :param name:
        :return:
        """
        self._name = name

    # Tasks
    @property
    def tasks(self):
        """
        :return: Tasks list
        """
        return self._tasks

    @tasks.setter
    def tasks(self, tasks):
        """
        Setting tasks

        :param tasks: Task objects list
        :return:
        """
        self._tasks = tasks

    def add_task(self, task: Task):
        """
        Add new task to tasks list, if task exist it will through error.

        :param task:
        :return: raise ValueError if tasks exists
        """
        for t in self._tasks:
            if t.name == task.name:
                raise ValueError("Task with same name: " + task.name + " exists")
        self._tasks.append(task)

    def add_tasks(self, tasks: List[Task]):
        """
        Add all given tasks to the workload.

        :param tasks: Task objects list
        :return:
        """
        for task in tasks:
            self.add_task(task)

    def del_task(self, task: Task):
        """
        Delete task from tasks list.

        :param task:
        :return:
        """
        if task not in self._tasks:
            return
        i = 0
        self._tasks.remove(task)
        while i < len(self._connections):
            con = self._connections[i]
            if con.source.name == task.name or con.target.name == task.name:
                self._connections.pop(i)
                del con
            else:
                i += 1

    def del_task_by_name(self, task_name):
        """
        Delete task by task name, nothing happens if task does not exist.

        :param task_name:
        :return:
        """
        to_del = None
        for t in self._tasks:
            if t.name == task_name:
                to_del = t
                break
        if to_del is not None:
            self._tasks.remove(to_del)
        i = 0
        while i < len(self._connections):
            con = self._connections[i]
            if con.source.name == to_del.name or con.target.name == to_del.name:
                self._connections.pop(i)
                del con
            else:
                i += 1

    def is_task_exist(self, task_name):
        """
        Checks if task exist by task name.

        :param task_name:
        :return: True if task exist, False otherwise.
        """
        for t in self._tasks:
            if t.name == task_name:
                return True
        return False

    def get_task(self, task_name):
        """
        Getting task object by task name.

        :param task_name:
        :return: Task
        """
        for task in self._tasks:
            if task.name == task_name:
                return task
        return None

    # Connections
    @property
    def connections(self):
        """
        :return: Connections list
        """
        return self._connections

    @connections.setter
    def connections(self, connections):
        self._connections = connections

    def connect_tasks(self, name, source: Task, target: Task, init=0, put_samples=1, get_samples=1, buf_size=1):
        """
        Connects source to target with proper attributes.

        :param name: connection name
        :param source: source Task
        :param target: target Task
        :param init:
        :param put_samples:
        :param get_samples:
        :param buf_size:
        :return:
        """
        for con in self._connections:
            if con.name == name:
                raise ValueError("Connection with same name: " + con.name + " exists")
        self._connections.append(Connection(name, source, target, init, put_samples, get_samples, buf_size))

    def del_connection(self, con_name):
        """
        Delete connection by connection name, nothing happens if connection does not exist.

        :param con_name:
        :return: True if deleted, False else.
        """
        to_del = None
        for con in self._connections:
            if con.name == con_name:
                to_del = con
                break
        if to_del is not None:
            self._connections.remove(to_del)
            del to_del
            return True
        return False

    def disconnect_tasks(self, source: Task, target: Task):
        """
        Disconnecting tasks

        :param source:
        :param target:
        :return:
        """
        to_del = None
        for con in self._connections:
            if con.source.name == source.name and con.target.name == target.name:
                to_del = con
                break
        if to_del is not None:
            self._connections.remove(to_del)
            del to_del

    def get_start_tasks(self):
        """
        Getting all start tasks of the workload.

        :return: Tasks list.
        """
        start_tasks = list()
        for t in self._tasks:
            if t.type == TYPES.START:
                start_tasks.append(t)
        return start_tasks

    def get_end_tasks(self):
        """
        Getting all end tasks of the workload.

        :return: Tasks list.
        """
        end_tasks = list()
        for t in self._tasks:
            if t.type == TYPES.END:
                end_tasks.append(t)
        return end_tasks

    def get_first_tasks(self, father_name=''):
        """
        Returns a list of the tuples that represent the tasks that trigger by start tasks: (father path, task obj)

        :param father_name:
        :return: tuples list (father path, task obj)
        """
        first_tasks = list()
        for con in self.connections:
            if con.source.type == TYPES.START:
                if con.target.type == TYPES.WORKLOAD:
                    first_tasks.extend(con.target.workload.get_first_tasks(father_name + con.target.name +
                                                                           NAME_SEPARATOR))
                else:
                    first_tasks.append((father_name, con.target))
        return first_tasks

    def get_last_tasks(self, father_name=''):
        """
        Returns a list of the tuples that represent the last tasks that trigger the end tasks: (father path, task obj)

        :param father_name:
        :return: tuples list (father path, task obj)
        """
        last_tasks = list()
        for con in self.connections:
            if con.target.type == TYPES.END:
                if con.source.type == TYPES.WORKLOAD:
                    last_tasks.extend(
                        con.source.workload.get_last_tasks(father_name + con.source.name + NAME_SEPARATOR))
                else:
                    last_tasks.append((father_name, con.source))
        return last_tasks

    def to_pnml_model(self):
        """
        Converting workload to pnml model.

        :return: Pnml model
        """
        net = PnmlModel.Net(transitions=[], places=[], arcs=[])
        for task in self._tasks:
            if task.type == TYPES.START:
                net.add_place(PnmlModel.Place(task.name, id=task.name, type=PnmlModel.Place.Type.START,
                                              iterations=task.get_attribute(TaskMetaData.ITERATIONS, 1),
                                              wait_delay=task.get_attribute(TaskMetaData.WAIT_DELAY, 0),
                                              start_delay=task.get_attribute(TaskMetaData.START_DELAY, 0)))
                net.add_transition(PnmlModel.Transition(TRIGGER_OUT + task.name, id=TRIGGER_OUT + task.name, runtime=0))
                net.add_arc(PnmlModel.Arc(task.name, TRIGGER_OUT + task.name,
                                          id=task.name + NAME_SEPARATOR + TRIGGER_OUT + task.name,
                                          weight=1))
            elif task.type == TYPES.END:
                net.add_place(PnmlModel.Place(task.name, id=task.name, type=PnmlModel.Place.Type.END))
                net.add_transition(PnmlModel.Transition(TRIGGER_IN + task.name, id=TRIGGER_IN + task.name, runtime=0))
                net.add_arc(PnmlModel.Arc(TRIGGER_IN + task.name, task.name,
                                          id=TRIGGER_IN + task.name + NAME_SEPARATOR + task.name,
                                          weight=1))
            elif task.type == TYPES.WORKLOAD:
                net.add_transition(PnmlModel.Transition(task.name, id=task.name, runtime=task.processing_cycles,
                                                        type=PnmlModel.Transition.Type.WORKLOAD))
            else:
                tran = PnmlModel.Transition(task.name, name=task.name, id=task.name, cycles=task.processing_cycles,
                                            memory=task.read_bytes + task.write_bytes,
                                            read_percentage=task.read_bytes / (task.read_bytes+task.write_bytes) * 100
                                            if task.read_bytes + task.write_bytes != 0 else 0)
                for att, val in task.attributes.items():
                    tran.set_attribute(att, val)

                net.add_transition(tran)

        for con in self._connections:
            if con.source.type == TYPES.START:
                net.add_place(PnmlModel.Place("b", id=con.source.name + NAME_SEPARATOR + con.target.name,
                                              buff_size=1))
                net.add_arc(PnmlModel.Arc(TRIGGER_OUT + con.source.name,
                                          con.source.name + NAME_SEPARATOR + con.target.name,
                                          id="pre__" + con.source.name + NAME_SEPARATOR + con.target.name,
                                          weight=con.get_samples))
                net.add_arc(PnmlModel.Arc(con.source.name + NAME_SEPARATOR + con.target.name, con.target.name,
                                          id="post__" + con.source.name + NAME_SEPARATOR + con.target.name,
                                          weight=1))
            elif con.target.type == TYPES.END:
                net.add_place(PnmlModel.Place("b", id=con.source.name + NAME_SEPARATOR + con.target.name,
                                              buff_size=1))
                net.add_arc(PnmlModel.Arc(con.source.name, con.source.name + NAME_SEPARATOR + con.target.name,
                                          id="pre__" + con.source.name + "__" + con.target.name,
                                          weight=con.put_samples))
                net.add_arc(PnmlModel.Arc(con.source.name + NAME_SEPARATOR + con.target.name,
                                          TRIGGER_IN + con.target.name,
                                          id="post__" + con.source.name + "__" + con.target.name,
                                          weight=1))
            else:
                place = PnmlModel.Place("b", id=con.source.name + "__" + con.target.name + "__p",
                                        init_count=con.init, buff_size=con.buf_size)
                net.add_place(place)
                net.add_arc(PnmlModel.Arc(con.source.name, place.id,
                                          id="pre__" + con.source.name + "__" + con.target.name,
                                          weight=con.put_samples))
                net.add_arc(PnmlModel.Arc(place.id, con.target.name,
                                          id="post__" + con.source.name + "__" + con.target.name,
                                          weight=con.get_samples))
        return PnmlModel([net])

    @property
    def attributes(self):
        return self._attributes

    def attach_attribute(self, attribute, value):
        """
        Attaching new attribute to workload, overwrite existing one.

        :param attribute:
        :param value:
        :return:
        """
        self._attributes[attribute] = value

    def get_attribute(self, attribute, default=None):
        """
        Getting workload attribute

        :param attribute:
        :param default: default value if attribute does not exist, default=None
        :return:
        """
        return self._attributes.get(attribute, default)

    def draw(self, file_name, view=False, format_="svg", keep_gv=False):
        """
        Drawing system platform

        :param file_name:
        :param view:
        :param format_:
        :param keep_gv:
        :return:
        """
        return self.to_pnml_model().draw(file_name, view=view, format_=format_, keep_gv=keep_gv)

    def _repr_svg_(self):
        """
        Jupyter integration. This will be called by Jupyter to display the object.

        :return: svg code
        """
        fd, tmp_file = tempfile.mkstemp(".svg")
        os.close(fd)
        self.draw(tmp_file, format_='svg', view=False)
        with open(tmp_file, 'r') as stream:
            text = stream.read()
        os.unlink(tmp_file)
        return text
