# List of pre-defined Petri Net attributes

NAME = "name"
FREQUENCY = "frequency"
LATENCY = "latency"
MEMORY = "memory"
READ_PERCENTAGE = "read_percentage"
CPU_AFFINITY = "cpu_affinity"
HW_RESOURCE = "hw_resource"
MIN_RUNTIME = "min_runtime"
AVG_RUNTIME = "avg_runtime"
MAX_RUNTIME = "max_runtime"
RUNTIME = "runtime"
CYCLES = "cycles"
PRIORITY = "priority"
START_DELAY = "start_delay"
WAIT_DELAY = "wait_delay"
ITERATIONS = "iterations"
INVOKES = "invokes"
CONC_RUNTIME = "conc_runtime"
CONC_READ_PERCENTAGE = "conc_read_percentage"
CONC_MEMORY = "conc_memory"
CONC_AFFINITY = "concurrent_affinity"
PREFIX_RUNTIME = "prefix_runtime"
PREFIX_AFFINITY = "prefix_affinity"
PREFIX_CONC_RUNTIME = "prefix_conc_runtime"
PREFIX_CONC_AFFINITY = "prefix_conc_affinity"
POSTFIX_RUNTIME = "postfix_runtime"
POSTFIX_AFFINITY = "postfix_affinity"
SWITCH_OVERHEAD = "switch_overhead"  # overhead between the time a task becomes ready and the actual execution
RUNNING_TRANSITIONS = 'RUNNING_TRANSITIONS'
PMC = 'pmc'
CLOCKS = 'clocks'
TRACE_INFO = 'trace_info'
ALIGN_TO_CLOCK = 'align_to_clock'
OP_TYPE = 'op_type'  # disk operation type
OP_SIZE = 'op_size'  # disk operation size
OP_PATH = 'op_path'  # disk operation path
DISK_NUM = 'disk_num'  # disk number for disk operation

WEIGHT = "weight"
BUFFER_SIZE = "buff_size"
INIT_COUNT = "init_count"

TYPE = "type"
FEATURE = 'feature'  # feature attribute used to map a task to a sub-feature

# Transition types
READ = "read"
PROCESSING = "processing"
WRITE = "write"

DATA_BYTES = "data_bytes"

# attribure_types maps attribute name to corresponding type
ATTR_2_TYPE = {
    NAME: str,
    FREQUENCY: float,
    LATENCY: float,
    MEMORY: float,
    READ: float,
    WRITE: float,
    READ_PERCENTAGE: float,
    CPU_AFFINITY: str,
    HW_RESOURCE: str,
    MIN_RUNTIME: float,
    AVG_RUNTIME: float,
    MAX_RUNTIME: float,
    RUNTIME: float,
    CYCLES: int,
    PRIORITY: int,
    START_DELAY: float,
    CONC_RUNTIME: float,
    CONC_READ_PERCENTAGE: float,
    CONC_MEMORY: float,
    CONC_AFFINITY: str,
    PREFIX_RUNTIME: float,
    PREFIX_AFFINITY: str,
    PREFIX_CONC_RUNTIME: float,
    PREFIX_CONC_AFFINITY: str,
    POSTFIX_RUNTIME: float,
    POSTFIX_AFFINITY: str,
    WEIGHT: int,
    BUFFER_SIZE: int,
    INIT_COUNT: int,
    TYPE: str,
    SWITCH_OVERHEAD: float,
}
