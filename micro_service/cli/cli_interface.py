from abc import ABC, abstractmethod

class ICommandLineHandler(ABC):

    @abstractmethod
    def description(self):
        """
        Should return description string for this sub-command.
        """
        raise (NotImplementedError())

    @abstractmethod
    def exec(self, args):
        """
        Execute sub-command with the specified arguments.
        :param args: list of command line arguments
        :return: application status (int, zero when OK, <0 when an error occurred).
        """

        raise (NotImplementedError())
