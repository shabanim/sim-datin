"""
**PMC -Performance Monitoring Counters-** defines counters structure.

Each task has its own counters.

"""


class Counter:
    """
    Counters, represents tasks trace counters details

    :param name: Counter name
    :param value: Counter value
    :param description: Help text describes counter
    """
    def __init__(self, name, value, description=''):
        self._name = name
        self._value = value
        self._description = description

    @property
    def name(self):
        """
        :return: name
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Setting counter name

        :param name:
        :return:
        """
        self._name = name

    @property
    def value(self):
        """
        :return: value
        """
        return self._value

    @value.setter
    def value(self, value):
        """
        Setting counter value

        :param value:
        :return:
        """
        self._value = value
