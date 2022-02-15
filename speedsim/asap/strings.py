"""
Definition of all strings used in project
"""

import pnets.attributes as pn_attr


# Components naming
class ComponentDesc:
    NAME = "Name"
    STATE = "State"
    PERIOD = "Period"
    CLOCK = "Clock"
    CLOCKS = "Clocks"
    MEMORIES = "Memories"
    IPS = "IPs"
    BUSES = "Buses"
    INITIATORS = "Initiators"
    TYPE = "Type"
    TARGETS = "Targets"
    BUS_WIDTH = "Bus_width"
    LATENCY = "Latency"
    SIZE = "Size"
    DRIVERS = "Drivers"
    PORTS = "Ports"
    EXEC_UNITS = "Executing_Units"
    GLOBAL_CLOCK = "__GLOBAL_CLOCK__"


class StateDesc:
    LEAKAGE_POWER = "Leakage_Power"
    VOLTAGE = "Voltage"
    ENTRANCE_LATENCY = "Entrance_Latency"
    EXIT_LATENCY = "Exit_Latency"
    TRIGGER_IN = "Trigger_In"
    CONDITION = "Condition"
    POWER_STATE = "Power_State"
    POWER_STATES = "Power_States"
    EXPRESSIONS = "Expressions"
    EXPRESSION = "Expression"
    SYSTEM_STATES = "System_States"
    IDLE_TIME = "Idle_Time"
    IP_STATES = "Ip_States"
    ACTIVE_STATE = "Active_State"
    REFERENCE_FREQUENCY = "Reference_Frequency"
    REFERENCE_DYNAMIC_POWER = "Reference_Dynamic_Power"
    OPPOSITE = "OPPOSITE"
    EQUAL = "="
    LESS_EQUAL = "<="
    FORCES = "FORCES"
    CONSTRAINTS = "CONSTRAINTS"
    DEFAULT = "default"


class ResourceDesc:
    IP = "IP"
    DRIVER = "DRIVER"
    EX_U = "EXECUTING_UNIT"
    BUS = "BUS"
    MEMORY = "MEMORY"
    PORT = "PORT"
    HW_COMPONENT = "HW_COMPONENT"
    CLOCK = 'CLOCK'


class TaskMetaData:
    TASK_TYPE = "TASK_TYPE"
    BASE_NAME = "BASE_NAME"
    FEATURE_TASK_NAME = "FEATURE_TASK_NAME"
    ITERATIONS = "iterations"
    WAIT_DELAY = "wait_delay"
    START_DELAY = "start_delay"
    RESOURCE = "RESOURCE"
    TASK_RUNTIME = "TASK_RUNTIME"
    TASK_ROUTING_PATH = "TASK_ROUTING_PATH"
    TASK_MEMORIES = "TASK_MEMORIES"
    GATING = 'GATING'


# Mapping
class MappingDesc:
    MAPPING = "MAPPING"
    TASK_ENTRY = "TASK"
    FEATURE_ENTRY = "FEATURE"
    IP_ENTRY = "IP"
    FEATURE_TASK_ENTRY = "FEATURE_TASK"
    MEMORY_TARGET = "MEMORY_TARGET"
    MEMORY_TARGETS = "MEMORY_TARGETS"
    RESOURCE = "RESOURCE"


class SchedulingState:
    NULL = "NULL"  # NULL resource.
    NAN = "NAN"  # Could not find resource.
    SCHEDULED = "SCHEDULED"  # Found resource


PMMLPreDefinedAtts = [pn_attr.HW_RESOURCE, pn_attr.PROCESSING, pn_attr.READ_PERCENTAGE, pn_attr.MEMORY,
                      pn_attr.CYCLES, pn_attr.RUNTIME, pn_attr.PMC, pn_attr.NAME]

# General
COMPONENT = "COMPONENT"
RESOURCE = "RESOURCE"
TYPE = "TYPE"
TASK = "task"
RPW = "RPW"
S_2_US = 10**6
US_2_S = 10**-6
NS = 10**-9
MB_TO_B = 1024**2
RUNTIME = "runtime"
NAME_SEPARATOR = "/"
TRIGGER_IN = "trigger_in_"
TRIGGER_OUT = "trigger_out_"
SIM_RES_FILE_NAME = "simulation_results.csv"
PENALTY = "PENALTY"
MIN_CYCLES = 1000
START_END_LIST = ['START/start_trigger', 'END/end_trigger', 'trigger_out_start', 'trigger_in_end']
SPLIT = "split"
TASK_SPLIT_COUNT = 'TASK_SPLIT_COUNT'
TASK_ACTIVATION_COUNT = 'TASK_ACTIVATION_COUNT'
WORKLOAD = "workload"
START_TRIGGER = "start_trigger"
END_TRIGGER = "end_trigger"
GATING_TRIGGER = "gating_trigger_"
HW_ANALYSIS = "HW Analysis"
TASK_ANALYSIS = "Task Analysis"
AND = 'AND'
OR = 'OR'
WLTASK_NAME = 'WLTASK_NAME'
MEMORY_PATH = 'MEMORY_PATH'
ALL_ELEMENTS = 'ALL_ELEMENTS'
ACTIVE_RUNTIME = 'ACTIVE_RUNTIME'
ATTRIBUTES = 'ATTRIBUTES'
TOOL_SPECIFIC = 'toolspecific'
ALIGNMENT_STATUS = 'ALIGNMENT_STATUS'
PENDING_ON_ALIGNMENT = 'PENDING_ON_ALIGNMENT'
RELEASED_FROM_ALIGNMENT = 'RELEASED_FROM_ALIGNMENT'
ALIGN_TO_CLOCK = 'align_to_clock'
