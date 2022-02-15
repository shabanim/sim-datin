"""
Defaults file - contain all ASAP default numbers and strings
"""


class PowerStates:
    SLEEP_STATE = 'C6'
    REFERENCE_LEAKAGE_POWER = 0
    REFERENCE_VOLTAGE = 0.8
    ENTRANCE_LATENCY = 1
    EXIT_LATENCY = 1
    TRIGGER = 15


class ActiveStates:
    ACTIVE_STATE = 'ACTIVE'
    REFERENCE_LEAKAGE_POWER = 50
    REFERENCE_VOLTAGE = 1
    REFERENCE_FREQUENCY = 800
    REFERENCE_DYNAMIC_POWER = 600


class GeneralPower:
    EXPRESSION_NAME = 'AlwaysTrue'
    IDLE_TIME = 0
